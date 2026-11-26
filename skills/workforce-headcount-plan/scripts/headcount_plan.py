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
<title>Workforce Headcount Plan · Zivo</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<!-- Zivo theme for pages built with the Tailwind CDN.
     Paste right after <script src="https://cdn.tailwindcss.com/3.4.16"></script>.
     Square radii, no shadows, Zivo tokens and fonts. See references/style-guide.md §8. -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Marcellus&family=Source+Sans+3:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<script>
tailwind.config = {
  theme: {
    borderRadius: { none: '0', sm: '0', DEFAULT: '0', md: '0', lg: '0', xl: '0', '2xl': '0', '3xl': '0', full: '9999px' },
    boxShadow: { sm: 'none', DEFAULT: 'none', md: 'none', lg: 'none', xl: 'none', '2xl': 'none', inner: 'none', none: 'none' },
    fontFamily: {
      display: ['"ABC Arizona Flare"', 'Marcellus', 'Georgia', 'serif'],
      sans: ['"ABC Arizona Sans"', '"Source Sans 3"', 'system-ui', 'sans-serif'],
    },
    extend: {
      colors: {
        zv: {
          ink: '#1A1A1A', off: '#F1F1EA', white: '#FFFFFF',
          red: '#F4364C', 'red-hover': '#E02A40', 'red-pressed': '#9E1528',
          ink80: 'rgba(26,26,26,.8)', ink60: 'rgba(26,26,26,.6)', ink40: 'rgba(26,26,26,.4)',
          ink30: 'rgba(26,26,26,.3)', ink20: 'rgba(26,26,26,.2)', line: 'rgba(26,26,26,.1)', ink05: 'rgba(26,26,26,.05)',
          success: '#0B7A43', 'success-bg': '#DDF7EA', 'success-fill': '#12B76A',
          warning: '#985704', 'warning-bg': '#FFF2DA', 'warning-fill': '#F69B10',
          error: '#B3172A', 'error-bg': '#FEE7EA', 'error-fill': '#D61F35',
          info: '#0B58BB', 'info-bg': '#E7F1FF', 'info-fill': '#1C7CE5',
          indigo: '#4636F2', aqua: '#12C3C9', orchid: '#C24BE6', citron: '#D4E030', midnight: '#1F188C',
        },
      },
    },
  },
};
</script>
<style>
  body { font-family: "ABC Arizona Sans", "Source Sans 3", system-ui, sans-serif; background: #F1F1EA; color: #1A1A1A; }
  h1, h2, h3, h4, .font-display { font-family: "ABC Arizona Flare", Marcellus, Georgia, serif; font-weight: 400 !important; font-style: normal; text-transform: none; }
  h1 { letter-spacing: -0.02em; }
  h2 { letter-spacing: -0.01em; }
  a { text-underline-offset: 2px; }
  .zv-dot { display: inline-block; width: 8px; height: 8px; background: currentColor; margin-right: 8px; vertical-align: 1px; }
  .zv-dot--red { background: #F4364C; }
  .zv-caption { font-size: 12px; line-height: 16px; text-transform: uppercase; letter-spacing: .04em; }
  .zv-wordmark { display: inline-flex; line-height: 0; }
  .zv-wordmark svg { height: 20px; width: auto; }
  .tabular { font-variant-numeric: tabular-nums; }
</style>
<style>
  *,::before,::after{border-radius:0;box-shadow:none}
  body{margin:0;background:#F1F1EA;color:#1A1A1A;font-size:16px;line-height:1.5;-webkit-font-smoothing:antialiased}
  .hero{background:#1A1A1A;color:#FFFFFF;padding:32px 0 48px}
  .hero-inner{max-width:1120px;margin:0 auto;padding:0 32px}
  .zv-header-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:24px;padding-bottom:10px;margin-bottom:40px;border-bottom:1px solid rgba(255,255,255,.3);color:rgba(255,255,255,.8);font-size:12px;line-height:16px;text-transform:uppercase;letter-spacing:.04em}
  .hero h1{font-size:56px;line-height:54px;color:#FFFFFF;max-width:22ch;margin:0}
  .hero-sub{margin:16px 0 0;color:rgba(255,255,255,.7);font-family:"ABC Arizona Flare",Marcellus,Georgia,serif;font-size:22px;line-height:28px;max-width:60ch}
  .hero-sub a{color:#FFFFFF;text-decoration:underline;text-underline-offset:2px}
  .page{max-width:1120px;margin:0 auto;padding:48px 32px}
  .page a{color:#1A1A1A;text-decoration:underline;text-underline-offset:2px}
  .card{background:#FFFFFF;border:1px solid rgba(26,26,26,.1);padding:24px;margin-bottom:24px;min-width:0}
  .card h2{font-size:22px;line-height:28px;margin-bottom:16px}
  .stat{font-family:"ABC Arizona Flare",Marcellus,Georgia,serif;font-size:40px;line-height:44px;margin-top:8px;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
  .stat.accent{color:#F4364C}
  .stat-label{font-size:12px;line-height:16px;text-transform:uppercase;letter-spacing:.04em;color:rgba(26,26,26,.6)}
  .page table{width:100%;border-collapse:collapse;font-size:14px;line-height:20px;background:#FFFFFF}
  .page th{text-align:left;font-weight:700;font-size:12px;line-height:16px;text-transform:uppercase;letter-spacing:.04em;color:rgba(26,26,26,.8);background:#FFFFFF;border-bottom:1px solid rgba(26,26,26,.3);padding:10px 12px}
  .page td{padding:10px 12px;border-bottom:1px solid rgba(26,26,26,.1);vertical-align:top;font-variant-numeric:tabular-nums}
  .page tbody tr:last-child td{border-bottom:none}
  .badge,.pill{display:inline-block;white-space:nowrap;padding:2px 10px;border-radius:999px;font-family:"ABC Arizona Sans","Source Sans 3",system-ui,sans-serif;font-size:12px;line-height:18px;font-weight:700;background:rgba(26,26,26,.05);color:#1A1A1A}
  .badge-good{background:#DDF7EA;color:#0B7A43}.badge-warn{background:#FFF2DA;color:#985704}
  .badge-bad{background:#FEE7EA;color:#B3172A}.badge-info{background:#E7F1FF;color:#0B58BB}
  .st-good{color:#0B7A43;font-weight:700}.st-warn{color:#985704;font-weight:700}.st-bad{color:#B3172A;font-weight:700}
  .zv-list li{display:flex;align-items:flex-start}
  .zv-list .zv-dot{flex:none;margin-top:8px}
  .site-footer{max-width:1120px;margin:0 auto;padding:24px 32px 40px;display:flex;align-items:center;gap:24px;flex-wrap:wrap;border-top:1px solid rgba(26,26,26,.1);font-size:14px;line-height:20px;color:rgba(26,26,26,.6)}
  .site-footer a{color:inherit}
  @media (max-width:560px){
    .hero-inner,.page,.site-footer{padding-left:20px;padding-right:20px}
    .hero h1{font-size:36px;line-height:36px}
    .zv-header-row{grid-template-columns:repeat(2,minmax(0,1fr));row-gap:8px}
    .stat{font-size:32px;line-height:36px}
    .card{padding:16px}
    .page th,.page td{padding:8px 6px}
  }
  .headline{background:#FFFFFF;border:1px solid rgba(26,26,26,.1);padding:24px;margin-bottom:24px}
  .stack{display:flex;align-items:flex-end;gap:8px;height:200px;padding-top:16px;border-bottom:1px solid rgba(26,26,26,.4)}
  .stack-col{flex:1;min-width:0;display:flex;flex-direction:column;justify-content:flex-end;align-items:center}
  .stack-col .text-xs{font-size:11px;line-height:14px;text-align:center;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
  .stack-bar{width:60%;background:#1A1A1A;min-height:2px}
  .qlabel{font-size:12px;line-height:16px;color:rgba(26,26,26,.6);margin-top:6px}
  .note{font-size:14px;line-height:20px;color:rgba(26,26,26,.6);margin-top:12px}
</style></head>
<body>
<header class="hero"><div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>Headcount plan</span><span><span id="generated"></span></span><span>Confidencial</span></div>
<h1>Plano de headcount</h1>
<p class="hero-sub">Contratações líquidas e custo incremental por cenário, função e trimestre.</p>
</div></header>
<main class="page">

<div class="headline">
  <div class="flex flex-wrap justify-between items-center gap-4">
    <div>
      <div class="stat-label">Contratações líquidas (Base)</div>
      <div class="stat" id="h-hires"></div>
    </div>
    <div>
      <div class="stat-label">Custo incremental anual (Base, run-rate)</div>
      <div class="stat accent" id="h-cost"></div>
    </div>
  </div>
  <div class="text-sm text-zv-ink80 mt-3" id="h-driver"></div>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2>Leitura</h2>
<ul class="space-y-2 zv-list" id="insights-list"></ul>
</div>

<div class="grid sm:grid-cols-2 gap-6">
<div class="card">
<h2 style="margin-bottom:4px">Headcount ao longo do tempo</h2>
<p class="text-xs text-zv-ink60 mb-2">Cenário Base, por trimestre</p>
<div class="stack" id="hc-stack"></div>
</div>
<div class="card">
<h2 style="margin-bottom:4px">Custo incremental por trimestre</h2>
<p class="text-xs text-zv-ink60 mb-2">Cenário Base</p>
<div class="stack" id="cost-stack"></div>
</div>
</div>

<div class="card">
<h2>Comparação de cenários</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Cenário</th><th>HC alvo</th><th>Net hires</th><th>Custo anual (run-rate)</th><th>Custo acumulado (horizonte)</th></tr></thead><tbody id="scen-tbody"></tbody></table></div>
</div>

<div class="card">
<h2>Roadmap por função, cenário Base</h2>
<div class="overflow-x-auto"><table><thead><tr id="roadmap-head"></tr></thead><tbody id="roadmap-tbody"></tbody></table></div>
<p class="note" id="cost-note"></p>
</div>

</main>
<footer class="site-footer">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=workforce-headcount-plan" aria-label="Zivo"><svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg></a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer>

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
    `<li class="flex items-start"><i class="zv-dot"></i><span>${i}</span></li>`).join('');
}

// Headcount stacked bars
const hcMax = Math.max(...base.headcount_by_quarter, 1);
document.getElementById('hc-stack').innerHTML = base.headcount_by_quarter.map((v, i) =>
  `<div class="stack-col"><div class="text-xs font-bold mb-1">${Math.round(v)}</div><div class="stack-bar" style="height:${(v/hcMax)*150}px"></div><div class="qlabel">Q${i+1}</div></div>`).join('');

const costMax = Math.max(...base.cost_by_quarter, 1);
document.getElementById('cost-stack').innerHTML = base.cost_by_quarter.map((v, i) =>
  `<div class="stack-col"><div class="text-xs font-bold mb-1">${fmt(v)}</div><div class="stack-bar" style="height:${(v/costMax)*150}px"></div><div class="qlabel">Q${i+1}</div></div>`).join('');

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
  fp.quarters.forEach(q => { row += `<td>${q.headcount}</td><td>+${q.net_hires}</td>`; });
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

    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=workforce-headcount-plan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
