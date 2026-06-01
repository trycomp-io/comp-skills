#!/usr/bin/env python3
"""
headcount_plan.py — Plano de headcount forward-looking amarrado ao crescimento.

A partir do headcount atual (total e/ou por função) + um driver de crescimento
(receita-alvo OU % de crescimento OU headcount-alvo) + ratios opcionais
(receita por colaborador, função:função, span de gestão), projeta o headcount
necessário por função por período, net new hires (incl. backfill por attrition),
e o custo incremental de folha. Gera 3 cenários (Conservador / Base / Agressivo).

Inputs:
  - Headcount atual: --headcount-total OU --functions-csv (function,headcount,loaded_cost_annual)
  - Driver (um): --target-revenue | --growth-pct | --target-headcount
  - Ratios: --rev-per-employee, --ratios "eng:product=2,sales:cs=3", --manager-span
  - --avg-loaded-cost (default por função se não vier no CSV), --horizon-quarters (4),
    --attrition-pct (0), --current-revenue (pra driver de receita)

Output: roadmap (função × trimestre), custo cumulativo por cenário, headline.

Uso:
    python3 headcount_plan.py --functions-csv funcs.csv \\
        --target-revenue 80000000 --current-revenue 20000000 \\
        --rev-per-employee 444000 --horizon-quarters 4 --attrition-pct 12
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "workforce-headcount-plan"
SKILL_VERSION = "1.0.0"

# Carga total média sobre o salário (encargos + benefícios) — nota informativa.
FULL_LOAD_FACTOR = 1.555
# Custo anual carregado default por colaborador quando não informado (R$).
DEFAULT_LOADED_COST = 240000.0

# Cenários: multiplicador aplicado ao crescimento líquido projetado.
SCENARIOS = [
    {"name": "Conservador", "key": "conservative", "growth_mult": 0.7},
    {"name": "Base", "key": "base", "growth_mult": 1.0},
    {"name": "Agressivo", "key": "aggressive", "growth_mult": 1.3},
]

FUNC_ALIASES = {
    "function": ["function", "funcao", "função", "area", "área", "departamento", "team", "time"],
    "headcount": ["headcount", "hc", "headcount_atual", "qtd", "quantidade", "colaboradores"],
    "loaded_cost_annual": ["loaded_cost_annual", "custo_anual", "custo", "loaded_cost", "custo_carregado_anual", "cost"],
}


def _norm(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii").strip().lower().replace(" ", "_")


def auto_detect(headers, aliases, key):
    h = {_norm(x): x for x in headers}
    for cand in aliases[key]:
        if _norm(cand) in h:
            return h[_norm(cand)]
    return None


def _f(v):
    if v is None or v == "":
        return None
    s = str(v).strip().replace("R$", "").strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def fmt_brl(v):
    s = f"{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def load_functions(path, avg_loaded):
    with path.open(newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        headers = r.fieldnames or []
        rows = list(r)
    cols = {k: auto_detect(headers, FUNC_ALIASES, k) for k in FUNC_ALIASES}
    if not cols.get("function") or not cols.get("headcount"):
        sys.exit("CSV de funções precisa de colunas function + headcount.")
    funcs = []
    for row in rows:
        name = (row.get(cols["function"]) or "").strip()
        hc = _f(row.get(cols["headcount"]))
        cost = _f(row.get(cols["loaded_cost_annual"])) if cols.get("loaded_cost_annual") else None
        if not name or hc is None:
            continue
        funcs.append({
            "function": name,
            "headcount": hc,
            "loaded_cost_annual": cost if cost else avg_loaded,
            "cost_assumed": cost is None,
        })
    return funcs


def parse_ratios(s):
    """'eng:product=2,sales:cs=3' → {('eng','product'): 2.0, ...}"""
    out = {}
    if not s:
        return out
    for part in s.split(","):
        if "=" not in part or ":" not in part:
            continue
        pair, val = part.rsplit("=", 1)
        a, b = pair.split(":", 1)
        v = _f(val)
        if v:
            out[(a.strip(), b.strip())] = v
    return out


def project_target_headcount(funcs, args):
    """
    Define o headcount-alvo TOTAL no fim do horizonte a partir do driver.
    Retorna (target_total, current_total, driver_label).
    """
    current_total = sum(f["headcount"] for f in funcs)

    if args.target_headcount is not None:
        return args.target_headcount, current_total, f"headcount-alvo {int(args.target_headcount)}"

    if args.target_revenue is not None and args.rev_per_employee:
        target = args.target_revenue / args.rev_per_employee
        return target, current_total, (
            f"receita-alvo {fmt_brl(args.target_revenue)} ÷ {fmt_brl(args.rev_per_employee)}/colaborador"
        )

    if args.growth_pct is not None:
        target = current_total * (1 + args.growth_pct / 100)
        return target, current_total, f"crescimento de {args.growth_pct:g}% no headcount"

    # Fallback: cresce headcount proporcional ao crescimento de receita.
    if args.target_revenue is not None and args.current_revenue:
        g = args.target_revenue / args.current_revenue
        return current_total * g, current_total, (
            f"headcount proporcional ao crescimento de receita ({g:.2f}x)"
        )

    sys.exit("Informe um driver: --target-headcount, --growth-pct, ou --target-revenue (+ --rev-per-employee ou --current-revenue).")


def build_scenario(funcs, current_total, target_total, args, growth_mult):
    """
    Distribui o headcount-alvo por função (proporcional ao mix atual),
    interpola linearmente por trimestre, e calcula net hires (incl. backfill).
    """
    horizon = args.horizon_quarters
    attrition_q = (args.attrition_pct / 100) / 4.0  # attrition trimestral pro-rata

    net_growth_total = (target_total - current_total) * growth_mult
    scen_target_total = current_total + net_growth_total

    # Mix proporcional ao headcount atual (ou igual se algum tiver 0).
    base_total = current_total if current_total > 0 else len(funcs)
    func_plan = []
    grand_cost_by_q = [0.0] * horizon
    grand_hires_by_q = [0.0] * horizon

    for f in funcs:
        share = (f["headcount"] / base_total) if current_total > 0 else (1.0 / len(funcs))
        target_hc = f["headcount"] + net_growth_total * share
        target_hc = max(target_hc, 0.0)

        quarters = []
        prev_hc = f["headcount"]
        cost_per_head = f["loaded_cost_annual"]
        for q in range(1, horizon + 1):
            # Interpolação linear do headcount entre atual e alvo.
            hc_q = f["headcount"] + (target_hc - f["headcount"]) * (q / horizon)
            growth_hires = max(hc_q - prev_hc, 0.0)
            backfill = prev_hc * attrition_q
            net_hires = growth_hires + backfill
            # Custo incremental do período = (headcount médio do trimestre − base inicial) × custo.
            avg_hc_q = (prev_hc + hc_q) / 2.0
            incr_cost_q = (avg_hc_q - f["headcount"]) * cost_per_head / 4.0
            incr_cost_q = max(incr_cost_q, 0.0)
            quarters.append({
                "q": q,
                "headcount": round(hc_q, 1),
                "net_hires": round(net_hires, 1),
                "incr_cost_quarter": round(incr_cost_q, 2),
            })
            grand_hires_by_q[q - 1] += net_hires
            grand_cost_by_q[q - 1] += incr_cost_q
            prev_hc = hc_q

        func_plan.append({
            "function": f["function"],
            "start_hc": round(f["headcount"], 1),
            "end_hc": round(target_hc, 1),
            "total_net_hires": round(sum(q["net_hires"] for q in quarters), 1),
            "cost_per_head": cost_per_head,
            "cost_assumed": f["cost_assumed"],
            "quarters": quarters,
        })

    # Custo anual incremental no estado final (run-rate): (end − start) × custo.
    incr_annual_runrate = sum(
        (fp["end_hc"] - fp["start_hc"]) * fp["cost_per_head"] for fp in func_plan
    )
    cumulative_cost = sum(grand_cost_by_q)  # custo somado ao longo do horizonte
    total_net_hires = sum(fp["total_net_hires"] for fp in func_plan)

    return {
        "target_total": round(scen_target_total, 1),
        "total_net_hires": round(total_net_hires, 1),
        "incr_annual_runrate": round(incr_annual_runrate, 2),
        "cumulative_cost_horizon": round(cumulative_cost, 2),
        "cost_by_quarter": [round(c, 2) for c in grand_cost_by_q],
        "hires_by_quarter": [round(h, 1) for h in grand_hires_by_q],
        "headcount_by_quarter": [
            round(current_total + (scen_target_total - current_total) * (q / horizon), 1)
            for q in range(1, horizon + 1)
        ],
        "functions": func_plan,
    }


def compute(funcs, args):
    target_total, current_total, driver_label = project_target_headcount(funcs, args)

    scenarios = {}
    for s in SCENARIOS:
        scenarios[s["key"]] = {
            "name": s["name"],
            "growth_mult": s["growth_mult"],
            **build_scenario(funcs, current_total, target_total, args, s["growth_mult"]),
        }

    base = scenarios["base"]
    insights = []
    insights.append(
        f"Driver: <strong>{driver_label}</strong>. Headcount atual <strong>{int(current_total)}</strong>, "
        f"alvo Base <strong>{int(base['target_total'])}</strong> em {args.horizon_quarters} trimestres."
    )
    insights.append(
        f"Cenário Base: <strong>{int(base['total_net_hires'])} contratações líquidas</strong> "
        f"(inclui backfill de attrition {args.attrition_pct:g}%) e custo incremental anual "
        f"em run-rate de <strong>{fmt_brl(base['incr_annual_runrate'])}</strong>."
    )
    insights.append(
        f"Faixa entre cenários: {int(scenarios['conservative']['total_net_hires'])} contratações "
        f"(Conservador) a {int(scenarios['aggressive']['total_net_hires'])} (Agressivo); "
        f"custo anual run-rate de {fmt_brl(scenarios['conservative']['incr_annual_runrate'])} a "
        f"{fmt_brl(scenarios['aggressive']['incr_annual_runrate'])}."
    )
    if args.attrition_pct > 0:
        insights.append(
            f"Backfill: com attrition de {args.attrition_pct:g}% ao ano sobre a base, parte das "
            f"contratações apenas repõe saídas — não é crescimento líquido de capacidade."
        )

    return {
        "meta": {
            "current_total": round(current_total, 1),
            "target_total_base": base["target_total"],
            "driver_label": driver_label,
            "horizon_quarters": args.horizon_quarters,
            "attrition_pct": args.attrition_pct,
            "full_load_factor": FULL_LOAD_FACTOR,
            "any_cost_assumed": any(f["cost_assumed"] for f in funcs),
        },
        "headline": {
            "total_net_hires": int(round(base["total_net_hires"])),
            "incr_annual_runrate": base["incr_annual_runrate"],
        },
        "scenarios": scenarios,
        "insights": insights,
    }


# ========== CLI output ==========


def print_result(r):
    h = r["headline"]
    m = r["meta"]
    print()
    print("=" * 66)
    print("  WORKFORCE HEADCOUNT PLAN")
    print("=" * 66)
    print(f"  Contratações líquidas (Base):   {h['total_net_hires']}")
    print(f"  Custo incremental anual (Base): {fmt_brl(h['incr_annual_runrate'])} (run-rate)")
    print(f"  Driver: {m['driver_label']}")
    print(f"  Horizonte: {m['horizon_quarters']} trimestres | Attrition: {m['attrition_pct']:g}%")
    print()
    print("  CENÁRIOS")
    print("  " + "-" * 58)
    print(f"    {'Cenário':<14} {'HC alvo':>9} {'Net hires':>11} {'Custo anual':>18}")
    for key in ("conservative", "base", "aggressive"):
        s = r["scenarios"][key]
        print(f"    {s['name']:<14} {int(s['target_total']):>9} {int(s['total_net_hires']):>11} {fmt_brl(s['incr_annual_runrate']):>18}")
    print()
    print("  ROADMAP POR FUNÇÃO (cenário Base — HC ao fim do horizonte)")
    print("  " + "-" * 58)
    print(f"    {'Função':<22} {'Início':>7} {'Fim':>7} {'Net hires':>11}")
    for fp in r["scenarios"]["base"]["functions"]:
        print(f"    {fp['function'][:22]:<22} {fp['start_hc']:>7g} {fp['end_hc']:>7g} {fp['total_net_hires']:>11g}")
    print()
    if m["any_cost_assumed"]:
        print(f"  Nota: custo anual carregado assumido onde não informado "
              f"({fmt_brl(DEFAULT_LOADED_COST)}/colaborador, ~{FULL_LOAD_FACTOR}x salário).")
    print()


# ========== HTML ==========


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Workforce Headcount Plan — Comp</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
  body{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b}
  .card{background:white;border-radius:12px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin-bottom:1.5rem}
  .stat{font-size:2rem;font-weight:800}
  .stat-label{font-size:.8rem;color:#64748b;text-transform:uppercase;font-weight:600}
  table{width:100%;border-collapse:collapse;font-size:.85rem}
  th{background:#1e293b;color:white;padding:.6rem;text-align:left;font-size:.72rem;text-transform:uppercase}
  td{padding:.6rem;border-bottom:1px solid #e2e8f0}
  .headline{background:#FFE600;border-radius:12px;padding:1.5rem 2rem;margin-bottom:1rem}
  .stack{display:flex;align-items:flex-end;gap:.5rem;height:200px;padding-top:1rem}
  .stack-col{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center}
  .stack-bar{width:60%;background:#1e293b;border-radius:6px 6px 0 0;min-height:2px}
  .qlabel{font-size:.72rem;color:#64748b;margin-top:.4rem}
  .note{font-size:.8rem;color:#64748b;margin-top:.75rem}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-5xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Workforce Headcount Plan</div>
<h1 class="text-3xl font-extrabold text-slate-900">Plano de headcount</h1>
<p class="text-sm text-slate-500 mt-2" id="generated"></p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="headline">
  <div class="flex flex-wrap justify-between items-center gap-4">
    <div>
      <div class="stat-label">Contratações líquidas (Base)</div>
      <div class="stat" id="h-hires"></div>
    </div>
    <div>
      <div class="stat-label">Custo incremental anual (Base, run-rate)</div>
      <div class="stat" id="h-cost"></div>
    </div>
  </div>
  <div class="text-sm text-slate-700 mt-3" id="h-driver"></div>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Leitura</h2>
<ul class="space-y-2" id="insights-list"></ul>
</div>

<div class="grid sm:grid-cols-2 gap-6">
<div class="card">
<h2 class="text-xl font-bold mb-1">Headcount ao longo do tempo</h2>
<p class="text-xs text-slate-500 mb-2">Cenário Base, por trimestre</p>
<div class="stack" id="hc-stack"></div>
</div>
<div class="card">
<h2 class="text-xl font-bold mb-1">Custo incremental por trimestre</h2>
<p class="text-xs text-slate-500 mb-2">Cenário Base</p>
<div class="stack" id="cost-stack"></div>
</div>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Comparação de cenários</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Cenário</th><th>HC alvo</th><th>Net hires</th><th>Custo anual (run-rate)</th><th>Custo acumulado (horizonte)</th></tr></thead><tbody id="scen-tbody"></tbody></table></div>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Roadmap por função — cenário Base</h2>
<div class="overflow-x-auto"><table><thead><tr id="roadmap-head"></tr></thead><tbody id="roadmap-tbody"></tbody></table></div>
<p class="note" id="cost-note"></p>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=workforce-headcount-plan" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });
const fmt = v => 'R$ ' + Math.round(v).toLocaleString('pt-BR');

const base = DATA.scenarios.base;
document.getElementById('h-hires').textContent = DATA.headline.total_net_hires;
document.getElementById('h-cost').textContent = fmt(DATA.headline.incr_annual_runrate);
document.getElementById('h-driver').textContent = 'Driver: ' + DATA.meta.driver_label + ' · horizonte ' + DATA.meta.horizon_quarters + ' trimestres · attrition ' + DATA.meta.attrition_pct + '%';

if (DATA.insights.length) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li class="flex items-start"><span class="text-rose-500 font-bold mr-2">●</span><span>${i}</span></li>`).join('');
}

// Headcount stacked bars
const hcMax = Math.max(...base.headcount_by_quarter, 1);
document.getElementById('hc-stack').innerHTML = base.headcount_by_quarter.map((v, i) =>
  `<div class="stack-col"><div class="text-xs font-bold mb-1">${Math.round(v)}</div><div class="stack-bar" style="height:${(v/hcMax)*150}px"></div><div class="qlabel">Q${i+1}</div></div>`).join('');

const costMax = Math.max(...base.cost_by_quarter, 1);
document.getElementById('cost-stack').innerHTML = base.cost_by_quarter.map((v, i) =>
  `<div class="stack-col"><div class="text-xs font-bold mb-1">${fmt(v)}</div><div class="stack-bar" style="height:${(v/costMax)*150}px;background:#0ea5e9"></div><div class="qlabel">Q${i+1}</div></div>`).join('');

// Scenario table
const order = ['conservative','base','aggressive'];
document.getElementById('scen-tbody').innerHTML = order.map(k => {
  const s = DATA.scenarios[k];
  const bold = k === 'base' ? 'style="font-weight:700"' : '';
  return `<tr ${bold}><td>${esc(s.name)}</td><td>${Math.round(s.target_total)}</td><td>${Math.round(s.total_net_hires)}</td><td>${fmt(s.incr_annual_runrate)}</td><td>${fmt(s.cumulative_cost_horizon)}</td></tr>`;
}).join('');

// Roadmap table (function × quarter)
const hq = DATA.meta.horizon_quarters;
let head = '<th>Função</th><th>Início</th>';
for (let q=1;q<=hq;q++) head += `<th>Q${q} HC</th><th>Q${q} hires</th>`;
head += '<th>Net hires</th>';
document.getElementById('roadmap-head').innerHTML = head;
document.getElementById('roadmap-tbody').innerHTML = base.functions.map(fp => {
  let row = `<td><strong>${esc(fp.function)}</strong></td><td>${fp.start_hc}</td>`;
  fp.quarters.forEach(q => { row += `<td>${q.headcount}</td><td class="text-emerald-700">+${q.net_hires}</td>`; });
  row += `<td><strong>${fp.total_net_hires}</strong></td>`;
  return `<tr>${row}</tr>`;
}).join('');

if (DATA.meta.any_cost_assumed) {
  document.getElementById('cost-note').textContent = 'Nota: custo anual carregado assumido onde não informado no CSV (~' + DATA.meta.full_load_factor + 'x salário, encargos + benefícios).';
}
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Plano de headcount forward-looking amarrado ao crescimento.")
    p.add_argument("--functions-csv", type=Path, help="CSV: function,headcount,loaded_cost_annual")
    p.add_argument("--headcount-total", type=float, help="Headcount total atual (se não usar CSV)")
    # Drivers
    p.add_argument("--target-revenue", type=float, help="Receita-alvo no fim do horizonte (R$)")
    p.add_argument("--current-revenue", type=float, help="Receita atual (R$) — pra driver de receita")
    p.add_argument("--growth-pct", type=float, help="Crescimento %% do headcount no horizonte")
    p.add_argument("--target-headcount", type=float, help="Headcount-alvo total no fim do horizonte")
    # Ratios
    p.add_argument("--rev-per-employee", type=float, help="Receita por colaborador (R$/ano)")
    p.add_argument("--ratios", help="'eng:product=2,sales:cs=3' (informativo)")
    p.add_argument("--manager-span", type=float, help="Span de gestão (informativo)")
    # Custos & horizonte
    p.add_argument("--avg-loaded-cost", type=float, default=DEFAULT_LOADED_COST, help=f"Custo anual carregado default por colaborador (default {DEFAULT_LOADED_COST:g})")
    p.add_argument("--horizon-quarters", type=int, default=4, help="Horizonte em trimestres (default 4)")
    p.add_argument("--attrition-pct", type=float, default=0.0, help="Attrition anual %% pra backfill (default 0)")
    p.add_argument("--output", type=Path, help="Caminho HTML (default: ./workforce-headcount-plan-<ts>.html)")
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    if args.functions_csv:
        funcs = load_functions(args.functions_csv, args.avg_loaded_cost)
        if not funcs:
            sys.exit("Nenhuma função válida no CSV.")
    elif args.headcount_total is not None:
        funcs = [{"function": "Total", "headcount": args.headcount_total,
                  "loaded_cost_annual": args.avg_loaded_cost, "cost_assumed": True}]
    else:
        sys.exit("Informe --functions-csv ou --headcount-total.")

    r = compute(funcs, args)
    print_result(r)

    out = args.output or Path.cwd() / f"workforce-headcount-plan-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(r, out)
    print(f"  HTML gerado: {out}")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=workforce-headcount-plan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
