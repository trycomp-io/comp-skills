#!/usr/bin/env python3
"""
initiative_roi.py — Business case / ROI de uma iniciativa de People.

Calcula ROI%, payback em meses, net benefit acumulado em 3 anos e sensibilidade
(Conservador/Esperado/Otimista) pra defender uma iniciativa de RH com o CFO/CEO.

Arquétipos de benefício suportados:
  (a) redução de attrition:  Δattrition_pct × headcount × cost_per_turnover
  (b) ganho de produtividade: pct_gain × affected_headcount × avg_loaded_cost
  (c) redução de time-to-fill: days_saved × cost_per_vacancy_day × hires_per_year
  (d) linha custom:           label + valor anual R$

Inputs principais:
  --initiative "Programa de retenção" --type retention
  --cost-onetime 150000 --cost-recurring 200000 --population 120
  --benefit-attrition "delta_pct=4,headcount=120,cost_per_turnover=120000"
  --benefit-productivity "pct_gain=3,headcount=120,avg_loaded_cost=180000"
  --benefit-ttf "days_saved=15,cost_per_vacancy_day=1500,hires_per_year=30"
  --benefit-custom "Redução de overtime=180000"

Uso:
    python3 initiative_roi.py --initiative "Retenção" --type retention \\
        --cost-onetime 150000 --cost-recurring 200000 --population 120 \\
        --benefit-attrition "delta_pct=4,headcount=120,cost_per_turnover=120000" \\
        --output roi.html
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "hr-initiative-roi"
SKILL_VERSION = "1.0.0"

# Sensibilidade: multiplicadores aplicados ao benefício anual.
SENSITIVITY = [
    {"name": "Conservador", "key": "conservative", "mult": 0.6},
    {"name": "Esperado", "key": "expected", "mult": 1.0},
    {"name": "Otimista", "key": "optimistic", "mult": 1.3},
]


def _f(v):
    if v is None or v == "":
        return None
    s = str(v).strip().replace("R$", "").strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def fmt_brl(v):
    neg = v < 0
    s = f"{abs(v):,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'-' if neg else ''}R$ {s}"


def parse_kv(s):
    """'delta_pct=4,headcount=120' → {'delta_pct':4.0,'headcount':120.0}"""
    out = {}
    if not s:
        return out
    for part in s.split(","):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        val = _f(v)
        if val is not None:
            out[k.strip().lower()] = val
    return out


def parse_custom(s):
    """'Label=180000' → {'label':..,'annual':..}"""
    if not s or "=" not in s:
        return None
    label, v = s.rsplit("=", 1)
    val = _f(v)
    if val is None:
        return None
    return {"label": label.strip(), "annual": val}


def build_benefit_lines(args):
    lines = []

    if args.benefit_attrition:
        kv = parse_kv(args.benefit_attrition)
        delta = kv.get("delta_pct", 0) / 100.0
        hc = kv.get("headcount") or args.population or 0
        cpt = kv.get("cost_per_turnover", 0)
        annual = delta * hc * cpt
        lines.append({
            "label": "Redução de attrition",
            "annual": round(annual, 2),
            "detail": f"Δ{kv.get('delta_pct', 0):g}pp × {int(hc)} pessoas × {fmt_brl(cpt)}/turnover",
        })

    if args.benefit_productivity:
        kv = parse_kv(args.benefit_productivity)
        pct = kv.get("pct_gain", 0) / 100.0
        hc = kv.get("headcount") or args.population or 0
        loaded = kv.get("avg_loaded_cost", 0)
        annual = pct * hc * loaded
        lines.append({
            "label": "Ganho de produtividade",
            "annual": round(annual, 2),
            "detail": f"{kv.get('pct_gain', 0):g}% × {int(hc)} pessoas × {fmt_brl(loaded)} custo carregado",
        })

    if args.benefit_ttf:
        kv = parse_kv(args.benefit_ttf)
        days = kv.get("days_saved", 0)
        cpvd = kv.get("cost_per_vacancy_day", 0)
        hpy = kv.get("hires_per_year", 0)
        annual = days * cpvd * hpy
        lines.append({
            "label": "Redução de time-to-fill",
            "annual": round(annual, 2),
            "detail": f"{days:g} dias × {fmt_brl(cpvd)}/dia de vaga × {int(hpy)} contratações/ano",
        })

    for cs in (args.benefit_custom or []):
        parsed = parse_custom(cs)
        if parsed:
            lines.append({
                "label": parsed["label"],
                "annual": round(parsed["annual"], 2),
                "detail": "linha custom (benefício anual informado)",
            })

    return lines


def compute(args):
    lines = build_benefit_lines(args)
    annual_benefit = round(sum(l["annual"] for l in lines), 2)

    cost_onetime = args.cost_onetime or 0.0
    cost_recurring = args.cost_recurring or 0.0
    total_cost_y1 = round(cost_onetime + cost_recurring, 2)

    # ROI ano 1 sobre o custo total do ano 1.
    net_y1 = round(annual_benefit - total_cost_y1, 2)
    roi_pct = round((net_y1 / total_cost_y1) * 100, 1) if total_cost_y1 > 0 else None

    # Payback: custo total inicial ÷ benefício mensal líquido de custo recorrente.
    monthly_net_benefit = (annual_benefit - cost_recurring) / 12.0
    if monthly_net_benefit > 0:
        payback_months = round(total_cost_y1 / monthly_net_benefit, 1)
    else:
        payback_months = None

    # 3 anos: ano 1 inclui one-time; anos 2-3 só recorrente.
    cum = []
    running = 0.0
    for y in range(1, 4):
        cost_y = cost_onetime + cost_recurring if y == 1 else cost_recurring
        net_y = annual_benefit - cost_y
        running += net_y
        cum.append({"year": y, "benefit": round(annual_benefit, 2), "cost": round(cost_y, 2),
                    "net_year": round(net_y, 2), "net_cumulative": round(running, 2)})
    net_3yr = cum[-1]["net_cumulative"]

    # Sensibilidade
    sens = []
    for s in SENSITIVITY:
        b = round(annual_benefit * s["mult"], 2)
        net = round(b - total_cost_y1, 2)
        roi = round((net / total_cost_y1) * 100, 1) if total_cost_y1 > 0 else None
        m_net = (b - cost_recurring) / 12.0
        pb = round(total_cost_y1 / m_net, 1) if m_net > 0 else None
        # 3yr cum
        run = 0.0
        for y in range(1, 4):
            cost_y = cost_onetime + cost_recurring if y == 1 else cost_recurring
            run += b - cost_y
        sens.append({
            "name": s["name"], "key": s["key"], "mult": s["mult"],
            "annual_benefit": b, "roi_pct": roi, "payback_months": pb,
            "net_3yr": round(run, 2),
        })

    insights = []
    if roi_pct is not None:
        insights.append(
            f"ROI ano 1: <strong>{roi_pct:g}%</strong> sobre custo total de {fmt_brl(total_cost_y1)} "
            f"(benefício anual {fmt_brl(annual_benefit)})."
        )
    if payback_months is not None:
        insights.append(f"Payback estimado em <strong>{payback_months:g} meses</strong>.")
    else:
        insights.append("Payback não calculável: benefício mensal líquido de custo recorrente ≤ 0 — revise as premissas.")
    insights.append(
        f"Net benefit acumulado em 3 anos: <strong>{fmt_brl(net_3yr)}</strong>."
    )
    cons = next(s for s in sens if s["key"] == "conservative")
    if cons["roi_pct"] is not None and cons["roi_pct"] > 0:
        insights.append(f"Mesmo no cenário Conservador (×0,6), o ROI permanece positivo ({cons['roi_pct']:g}%).")
    elif cons["roi_pct"] is not None:
        insights.append(f"Atenção: no cenário Conservador (×0,6) o ROI fica em {cons['roi_pct']:g}% — caso sensível às premissas.")

    return {
        "meta": {
            "initiative": args.initiative or "Iniciativa de People",
            "type": args.type or "—",
            "population": int(args.population) if args.population else None,
        },
        "costs": {
            "onetime": round(cost_onetime, 2),
            "recurring": round(cost_recurring, 2),
            "total_y1": total_cost_y1,
        },
        "benefit_lines": lines,
        "annual_benefit": annual_benefit,
        "headline": {
            "roi_pct": roi_pct,
            "payback_months": payback_months,
            "net_3yr": net_3yr,
        },
        "three_year": cum,
        "sensitivity": sens,
        "insights": insights,
    }


# ========== CLI output ==========


def print_result(r):
    h = r["headline"]
    m = r["meta"]
    c = r["costs"]
    print()
    print("=" * 64)
    print(f"  HR INITIATIVE ROI — {m['initiative']}")
    print("=" * 64)
    print(f"  ROI (ano 1):        {('%g%%' % h['roi_pct']) if h['roi_pct'] is not None else 'n/a'}")
    print(f"  Payback:            {('%g meses' % h['payback_months']) if h['payback_months'] is not None else 'n/a'}")
    print(f"  Net 3 anos:         {fmt_brl(h['net_3yr'])}")
    print(f"  Benefício anual:    {fmt_brl(r['annual_benefit'])}")
    print(f"  Custo total ano 1:  {fmt_brl(c['total_y1'])} (one-time {fmt_brl(c['onetime'])} + recorrente {fmt_brl(c['recurring'])})")
    print()
    print("  LINHAS DE BENEFÍCIO (anual)")
    print("  " + "-" * 56)
    for l in r["benefit_lines"]:
        print(f"    {l['label']:<28} {fmt_brl(l['annual']):>16}")
        print(f"      {l['detail']}")
    print()
    print("  SENSIBILIDADE")
    print("  " + "-" * 56)
    print(f"    {'Cenário':<14} {'Benefício/ano':>16} {'ROI':>8} {'Payback':>10} {'Net 3a':>16}")
    for s in r["sensitivity"]:
        roi = ("%g%%" % s["roi_pct"]) if s["roi_pct"] is not None else "n/a"
        pb = ("%gm" % s["payback_months"]) if s["payback_months"] is not None else "n/a"
        print(f"    {s['name']:<14} {fmt_brl(s['annual_benefit']):>16} {roi:>8} {pb:>10} {fmt_brl(s['net_3yr']):>16}")
    print()


# ========== HTML ==========


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HR Initiative ROI — Comp</title>
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
  .barwrap{display:flex;align-items:flex-end;gap:2rem;height:220px;padding-top:1rem}
  .bargroup{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center}
  .bar{width:70%;border-radius:6px 6px 0 0;min-height:2px}
  .blabel{font-size:.78rem;color:#64748b;margin-top:.4rem;text-align:center}
  .note{font-size:.8rem;color:#64748b;margin-top:.75rem}
  .pos{color:#059669}.neg{color:#dc2626}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-4xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">HR Initiative ROI</div>
<h1 class="text-3xl font-extrabold text-slate-900" id="title"></h1>
<p class="text-sm text-slate-500 mt-2" id="generated"></p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="headline">
  <div class="grid grid-cols-3 gap-4 text-center">
    <div><div class="stat-label">ROI (ano 1)</div><div class="stat" id="h-roi"></div></div>
    <div><div class="stat-label">Payback</div><div class="stat" id="h-payback"></div></div>
    <div><div class="stat-label">Net 3 anos</div><div class="stat" id="h-net3"></div></div>
  </div>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Leitura para o board</h2>
<ul class="space-y-2" id="insights-list"></ul>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-1">Custo vs benefício (ano 1)</h2>
<p class="text-xs text-slate-500 mb-2">A linha pontilhada marca o ponto de payback</p>
<div class="barwrap" id="cb-bars"></div>
<p class="note" id="payback-note"></p>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Linhas de benefício (anual)</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Benefício</th><th>Premissa</th><th>Anual</th></tr></thead><tbody id="ben-tbody"></tbody></table></div>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Sensibilidade</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Cenário</th><th>Mult.</th><th>Benefício/ano</th><th>ROI</th><th>Payback</th><th>Net 3 anos</th></tr></thead><tbody id="sens-tbody"></tbody></table></div>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Projeção 3 anos (cenário Esperado)</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Ano</th><th>Benefício</th><th>Custo</th><th>Net no ano</th><th>Net acumulado</th></tr></thead><tbody id="ty-tbody"></tbody></table></div>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=hr-initiative-roi" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('title').textContent = DATA.meta.initiative;
document.getElementById('generated').textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' }) + (DATA.meta.population ? ' · ' + DATA.meta.population + ' pessoas afetadas' : '');
const fmt = v => (v < 0 ? '-' : '') + 'R$ ' + Math.round(Math.abs(v)).toLocaleString('pt-BR');

document.getElementById('h-roi').textContent = DATA.headline.roi_pct != null ? (DATA.headline.roi_pct + '%') : 'n/a';
document.getElementById('h-payback').textContent = DATA.headline.payback_months != null ? (DATA.headline.payback_months + ' m') : 'n/a';
document.getElementById('h-net3').textContent = fmt(DATA.headline.net_3yr);

if (DATA.insights.length) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li class="flex items-start"><span class="text-rose-500 font-bold mr-2">●</span><span>${i}</span></li>`).join('');
}

// Cost vs benefit bars
const cost = DATA.costs.total_y1;
const ben = DATA.annual_benefit;
const mx = Math.max(cost, ben, 1);
document.getElementById('cb-bars').innerHTML = `
  <div class="bargroup"><div class="text-sm font-bold mb-1">${fmt(cost)}</div><div class="bar" style="height:${(cost/mx)*160}px;background:#dc2626"></div><div class="blabel">Custo total<br>(ano 1)</div></div>
  <div class="bargroup"><div class="text-sm font-bold mb-1">${fmt(ben)}</div><div class="bar" style="height:${(ben/mx)*160}px;background:#059669"></div><div class="blabel">Benefício<br>anual</div></div>`;
if (DATA.headline.payback_months != null) {
  document.getElementById('payback-note').textContent = 'Payback em ' + DATA.headline.payback_months + ' meses — o investimento se paga antes de ' + (DATA.headline.payback_months <= 12 ? 'completar o primeiro ano.' : (Math.ceil(DATA.headline.payback_months/12) + ' anos.'));
} else {
  document.getElementById('payback-note').textContent = 'Payback não calculável com as premissas atuais.';
}

document.getElementById('ben-tbody').innerHTML = DATA.benefit_lines.map(l =>
  `<tr><td><strong>${esc(l.label)}</strong></td><td class="text-slate-500">${esc(l.detail)}</td><td class="pos">${fmt(l.annual)}</td></tr>`).join('')
  + `<tr style="font-weight:700"><td>Total</td><td></td><td class="pos">${fmt(DATA.annual_benefit)}</td></tr>`;

document.getElementById('sens-tbody').innerHTML = DATA.sensitivity.map(s => {
  const bold = s.key === 'expected' ? 'style="font-weight:700"' : '';
  const roi = s.roi_pct != null ? (s.roi_pct + '%') : 'n/a';
  const pb = s.payback_months != null ? (s.payback_months + ' m') : 'n/a';
  const cls = s.net_3yr >= 0 ? 'pos' : 'neg';
  return `<tr ${bold}><td>${esc(s.name)}</td><td>${s.mult}x</td><td>${fmt(s.annual_benefit)}</td><td>${roi}</td><td>${pb}</td><td class="${cls}">${fmt(s.net_3yr)}</td></tr>`;
}).join('');

document.getElementById('ty-tbody').innerHTML = DATA.three_year.map(y => {
  const cls = y.net_cumulative >= 0 ? 'pos' : 'neg';
  return `<tr><td>Ano ${y.year}</td><td>${fmt(y.benefit)}</td><td>${fmt(y.cost)}</td><td>${fmt(y.net_year)}</td><td class="${cls}"><strong>${fmt(y.net_cumulative)}</strong></td></tr>`;
}).join('');
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Business case / ROI de uma iniciativa de People.")
    p.add_argument("--initiative", help="Nome da iniciativa")
    p.add_argument("--type", help="Tipo (retention, l&d, recruiting-tool, wellbeing, onboarding, etc.)")
    p.add_argument("--cost-onetime", type=float, default=0.0, help="Custo one-time (R$)")
    p.add_argument("--cost-recurring", type=float, default=0.0, help="Custo recorrente anual (R$)")
    p.add_argument("--population", type=float, help="População afetada (headcount)")
    # Benefícios
    p.add_argument("--benefit-attrition", help="'delta_pct=4,headcount=120,cost_per_turnover=120000'")
    p.add_argument("--benefit-productivity", help="'pct_gain=3,headcount=120,avg_loaded_cost=180000'")
    p.add_argument("--benefit-ttf", help="'days_saved=15,cost_per_vacancy_day=1500,hires_per_year=30'")
    p.add_argument("--benefit-custom", action="append", help="'Label=valor_anual' (pode repetir)")
    p.add_argument("--output", type=Path, help="Caminho HTML (default: ./hr-initiative-roi-<ts>.html)")
    args = p.parse_args()

    if not any([args.benefit_attrition, args.benefit_productivity, args.benefit_ttf, args.benefit_custom]):
        sys.exit("Informe ao menos uma linha de benefício (--benefit-attrition / --benefit-productivity / --benefit-ttf / --benefit-custom).")

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    r = compute(args)
    print_result(r)

    out = args.output or Path.cwd() / f"hr-initiative-roi-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(r, out)
    print(f"  HTML gerado: {out}")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=hr-initiative-roi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
