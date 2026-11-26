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
<title>HR initiative ROI · Zivo</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Marcellus&family=Source+Sans+3:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<style>
:root {
  --zivo-ink: #1A1A1A;
  --zivo-off-white: #F1F1EA;
  --zivo-white: #FFFFFF;
  --zivo-red: #F4364C;
  --zivo-red-hover: #E02A40;
  --zivo-red-pressed: #9E1528;
  --zivo-ink-80: rgba(26,26,26,.8);
  --zivo-ink-60: rgba(26,26,26,.6);
  --zivo-ink-40: rgba(26,26,26,.4);
  --zivo-ink-30: rgba(26,26,26,.3);
  --zivo-ink-20: rgba(26,26,26,.2);
  --zivo-ink-10: rgba(26,26,26,.1);
  --zivo-ink-05: rgba(26,26,26,.05);
  --zivo-success: #0B7A43; --zivo-success-bg: #DDF7EA; --zivo-success-fill: #12B76A;
  --zivo-warning: #985704; --zivo-warning-bg: #FFF2DA; --zivo-warning-fill: #F69B10;
  --zivo-error: #B3172A;   --zivo-error-bg: #FEE7EA;   --zivo-error-fill: #D61F35;
  --zivo-info: #0B58BB;    --zivo-info-bg: #E7F1FF;    --zivo-info-fill: #1C7CE5;
  --zivo-font-flare: "ABC Arizona Flare", Marcellus, Georgia, serif;
  --zivo-font-sans: "ABC Arizona Sans", "Source Sans 3", system-ui, -apple-system, "Segoe UI", sans-serif;
  --zivo-radius: 0;
  --gap: 24px;
}

* { box-sizing: border-box; border-radius: 0; box-shadow: none; }

body {
  margin: 0;
  font-family: var(--zivo-font-sans);
  font-size: 16px;
  line-height: 1.5;
  color: var(--zivo-ink);
  background: var(--zivo-off-white);
  -webkit-font-smoothing: antialiased;
}

h1, h2, h3, h4 {
  font-family: var(--zivo-font-flare);
  font-weight: 400;
  font-style: normal;
  text-transform: none;
  margin: 0 0 .4em;
}
h1 { font-size: 56px; line-height: 54px; letter-spacing: -0.02em; }
h2 { font-size: 32px; line-height: 36px; letter-spacing: -0.01em; }
h3 { font-size: 22px; line-height: 28px; }
h4 { font-size: 18px; line-height: 24px; }
p { margin: 0 0 1em; }
small, .small { font-size: 14px; line-height: 20px; }
.caption, .label {
  font-size: 12px; line-height: 16px; text-transform: uppercase;
  letter-spacing: .04em; color: var(--zivo-ink-60);
}
.muted { color: var(--zivo-ink-60); }
a { color: var(--zivo-ink); text-decoration: underline; text-underline-offset: 2px; }
a:hover { color: var(--zivo-ink-80); }

/* Square node / overline marker */
.zv-dot { display: inline-block; width: 8px; height: 8px; background: currentColor; margin-right: 8px; vertical-align: 1px; }
.zv-dot--red { background: var(--zivo-red); }

/* Header row: four captions over a 1px rule */
.zv-header-row {
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--gap);
  padding-bottom: 10px; margin-bottom: 40px;
  border-bottom: 1px solid var(--zivo-ink-30);
  font-size: 12px; line-height: 16px; text-transform: uppercase; letter-spacing: .04em;
}

/* Hero */
.hero { background: var(--zivo-ink); color: var(--zivo-white); padding: 32px 0 48px; }
.hero-inner { max-width: 1120px; margin: 0 auto; padding: 0 32px; }
.hero .zv-header-row { border-bottom-color: rgba(255,255,255,.3); color: rgba(255,255,255,.8); }
.hero h1 { color: var(--zivo-white); max-width: 22ch; }
.hero-sub { margin: 16px 0 0; color: rgba(255,255,255,.7); font-family: var(--zivo-font-flare); font-size: 22px; line-height: 28px; max-width: 60ch; }
.logo-tile { width: 56px; height: 56px; display: grid; place-items: center; background: var(--zivo-white); color: var(--zivo-ink); font-family: var(--zivo-font-flare); font-size: 28px; }
.logo-tile img { max-width: 44px; max-height: 44px; }

/* Page */
.page { max-width: 1120px; margin: 0 auto; padding: 48px 32px; }
.section { margin-bottom: 48px; }
.section > h2 { margin-bottom: 16px; }

/* Cards */
.card { background: var(--zivo-white); border: 1px solid var(--zivo-ink-10); padding: 24px; }
.card + .card { margin-top: var(--gap); }
.card h3 { margin-bottom: 12px; }

/* Stat strip */
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
.stat-card { background: var(--zivo-white); border: 1px solid var(--zivo-ink-10); padding: 20px; }
.stat-card .value { font-family: var(--zivo-font-flare); font-size: 40px; line-height: 44px; margin-top: 8px; font-variant-numeric: tabular-nums; }
.stat-card .value.accent { color: var(--zivo-red); }
.stat-card .context { font-size: 14px; line-height: 20px; color: var(--zivo-ink-80); margin-top: 8px; }
.trend-up { color: var(--zivo-success); }
.trend-down { color: var(--zivo-error); }
.trend-flat { color: var(--zivo-ink-60); }

/* Big number: one per page */
.big-number .value { font-family: var(--zivo-font-flare); font-size: 96px; line-height: 92px; letter-spacing: -0.02em; }
.big-number .rule { height: 1px; background: var(--zivo-ink); margin: 16px 0; }
.big-number .label { font-size: 22px; line-height: 28px; text-transform: none; letter-spacing: 0; color: var(--zivo-ink); }

/* Tables */
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; line-height: 20px; background: var(--zivo-white); }
thead th {
  text-align: left; font-weight: 700; font-size: 12px; line-height: 16px;
  text-transform: uppercase; letter-spacing: .04em; color: var(--zivo-ink-80);
  border-bottom: 1px solid var(--zivo-ink-30); padding: 10px 12px;
}
tbody td { padding: 10px 12px; border-bottom: 1px solid var(--zivo-ink-10); vertical-align: top; }
tbody tr:last-child td { border-bottom: none; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }

/* Buttons: square, one arrow */
.btn {
  display: inline-block; padding: 12px 16px; font-family: var(--zivo-font-sans); font-size: 16px; line-height: 20px;
  background: var(--zivo-ink); color: var(--zivo-white); border: 1px solid var(--zivo-ink);
  text-decoration: none; cursor: pointer;
}
.btn:hover { background: #333; color: var(--zivo-white); }
.btn-secondary { background: transparent; color: var(--zivo-ink); }
.btn-secondary:hover { background: var(--zivo-ink-05); color: var(--zivo-ink); }
.btn-primary { background: var(--zivo-red); border-color: var(--zivo-red); color: var(--zivo-white); }
.btn-primary:hover { background: var(--zivo-red-hover); border-color: var(--zivo-red-hover); }
.btn-primary:active { background: var(--zivo-red-pressed); }

/* Badges: the only rounded element */
.badge { display: inline-block; white-space: nowrap; padding: 2px 10px; border-radius: 999px; font-size: 12px; line-height: 18px; font-weight: 700; background: var(--zivo-ink-05); color: var(--zivo-ink); }
.badge-good { background: var(--zivo-success-bg); color: var(--zivo-success); }
.badge-warn { background: var(--zivo-warning-bg); color: var(--zivo-warning); }
.badge-bad  { background: var(--zivo-error-bg);   color: var(--zivo-error); }
.badge-info { background: var(--zivo-info-bg);    color: var(--zivo-info); }

/* Meters */
.meter { height: 8px; background: var(--zivo-ink-10); }
.meter > span { display: block; height: 100%; background: var(--zivo-ink); }

/* Callout: neutral note, no coloured side borders */
.callout { background: var(--zivo-white); border-top: 1px solid var(--zivo-ink); padding: 16px 0 0; }

/* Footer */
.site-footer {
  max-width: 1120px; margin: 0 auto; padding: 24px 32px 40px;
  display: flex; align-items: center; gap: 24px; flex-wrap: wrap;
  border-top: 1px solid var(--zivo-ink-10);
  font-size: 14px; line-height: 20px; color: var(--zivo-ink-60);
}
.site-footer a { color: inherit; }
.zv-wordmark { display: inline-flex; line-height: 0; }
.zv-wordmark svg { height: 20px; width: auto; }

@media (max-width: 560px) {
  .hero-inner, .page, .site-footer { padding-left: 20px; padding-right: 20px; }
  h1, .hero h1 { font-size: 36px; line-height: 36px; }
  h2 { font-size: 26px; line-height: 30px; }
  .zv-header-row { grid-template-columns: repeat(2, minmax(0, 1fr)); row-gap: 8px; }
  .big-number .value { font-size: 64px; line-height: 64px; }
}

@media print {
  body { background: var(--zivo-white); }
  .hero { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}

/* Report components */
.grid-2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:24px;align-items:start}
.grid-2 > .card + .card{margin-top:0}
.section-sub{font-size:14px;line-height:20px;color:var(--zivo-ink-60);margin:-8px 0 16px}
.insights{list-style:none;margin:0;padding:0}
.insights li{display:flex;align-items:flex-start;padding:10px 0;border-bottom:1px solid var(--zivo-ink-10)}
.insights li:first-child{padding-top:0}
.insights li:last-child{border-bottom:none;padding-bottom:0}
.insights .zv-dot{flex:none;margin-top:8px}
.hero .zv-header-row span{min-width:0;overflow-wrap:anywhere}
.callout{padding:16px 20px;border-bottom:1px solid var(--zivo-ink-10)}
.callout p:last-child{margin-bottom:0}
@media (max-width:560px){.stat-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.stat-card .value{font-size:32px;line-height:36px}}
td.num,th.num{white-space:nowrap}
@media (max-width:560px){.card{padding:16px}.stat-card .value{font-size:28px;line-height:32px;overflow-wrap:anywhere}}
.barwrap{display:flex;align-items:flex-end;gap:32px;height:240px;padding-top:16px;border-bottom:1px solid var(--zivo-ink-40)}
.bargroup{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center}
.bar{width:60%;max-width:200px;min-height:2px}
.bvalue{font-size:14px;line-height:20px;font-weight:700;margin-bottom:4px;font-variant-numeric:tabular-nums}
.blabels{display:flex;gap:32px}
.blabels div{flex:1;text-align:center;font-size:14px;line-height:20px;color:var(--zivo-ink-60);margin-top:8px}
.pos{color:var(--zivo-success)}.neg{color:var(--zivo-error)}
tr.strong td{font-weight:700}
</style></head>
<body>

<header class="hero">
<div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>HR initiative ROI</span><span id="generated"></span><span id="population"></span></div>
<h1 id="title"></h1>
<p class="hero-sub">Custo, benefício, payback e sensibilidade da iniciativa em 3 anos.</p>
</div>
</header>

<main class="page">

<section class="section">
<div class="stat-grid">
<div class="stat-card"><div class="label">ROI (ano 1)</div><div class="value accent" id="h-roi"></div><div class="context">Benefício menos custo, sobre o custo.</div></div>
<div class="stat-card"><div class="label">Payback</div><div class="value" id="h-payback"></div><div class="context">Meses até o investimento se pagar.</div></div>
<div class="stat-card"><div class="label">Net 3 anos</div><div class="value" id="h-net3"></div><div class="context">Cenário esperado, acumulado.</div></div>
</div>
</section>

<section class="section" id="insights-card" style="display:none;">
<h2>Leitura para o board</h2>
<div class="card"><ul class="insights" id="insights-list"></ul></div>
</section>

<section class="section">
<h2>Custo vs benefício (ano 1)</h2>
<div class="card">
<p class="small muted">Custo total do primeiro ano contra o benefício anual esperado, em R$.</p>
<div class="barwrap" id="cb-bars"></div>
<div class="blabels"><div>Custo total (ano 1)</div><div>Benefício anual</div></div>
<p class="small muted" style="margin-top:16px" id="payback-note"></p>
</div>
</section>

<section class="section">
<h2>Linhas de benefício (anual)</h2>
<div class="card table-wrap"><table><thead><tr><th>Benefício</th><th>Premissa</th><th class="num">Anual</th></tr></thead><tbody id="ben-tbody"></tbody></table></div>
</section>

<section class="section">
<h2>Sensibilidade</h2>
<div class="card table-wrap"><table><thead><tr><th>Cenário</th><th class="num">Mult.</th><th class="num">Benefício/ano</th><th class="num">ROI</th><th class="num">Payback</th><th class="num">Net 3 anos</th></tr></thead><tbody id="sens-tbody"></tbody></table></div>
</section>

<section class="section">
<h2>Projeção 3 anos (cenário esperado)</h2>
<div class="card table-wrap"><table><thead><tr><th>Ano</th><th class="num">Benefício</th><th class="num">Custo</th><th class="num">Net no ano</th><th class="num">Net acumulado</th></tr></thead><tbody id="ty-tbody"></tbody></table></div>
</section>

</main>

<footer class="site-footer">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=hr-initiative-roi" aria-label="Zivo"><svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg></a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('title').textContent = DATA.meta.initiative;
document.getElementById('generated').textContent = new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'short', year:'numeric' });
document.getElementById('population').textContent = DATA.meta.population ? DATA.meta.population + ' pessoas afetadas' : 'Uso interno';
const fmt = v => (v < 0 ? '-' : '') + 'R$ ' + Math.round(Math.abs(v)).toLocaleString('pt-BR');

document.getElementById('h-roi').textContent = DATA.headline.roi_pct != null ? (DATA.headline.roi_pct + '%') : 'n/a';
document.getElementById('h-payback').textContent = DATA.headline.payback_months != null ? (DATA.headline.payback_months + ' m') : 'n/a';
document.getElementById('h-net3').textContent = fmt(DATA.headline.net_3yr);

if (DATA.insights.length) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li><i class="zv-dot"></i><span>${i}</span></li>`).join('');
}

// Cost vs benefit bars (ink = cost, red = the highlighted benefit)
const cost = DATA.costs.total_y1;
const ben = DATA.annual_benefit;
const mx = Math.max(cost, ben, 1);
document.getElementById('cb-bars').innerHTML = `
  <div class="bargroup"><div class="bvalue">${fmt(cost)}</div><div class="bar" style="height:${(cost/mx)*180}px;background:#1A1A1A"></div></div>
  <div class="bargroup"><div class="bvalue">${fmt(ben)}</div><div class="bar" style="height:${(ben/mx)*180}px;background:#F4364C"></div></div>`;
if (DATA.headline.payback_months != null) {
  document.getElementById('payback-note').textContent = 'Payback em ' + DATA.headline.payback_months + ' meses: o investimento se paga antes de ' + (DATA.headline.payback_months <= 12 ? 'completar o primeiro ano.' : (Math.ceil(DATA.headline.payback_months/12) + ' anos.'));
} else {
  document.getElementById('payback-note').textContent = 'Payback não calculável com as premissas atuais.';
}

document.getElementById('ben-tbody').innerHTML = DATA.benefit_lines.map(l =>
  `<tr><td><strong>${esc(l.label)}</strong></td><td class="muted">${esc(l.detail)}</td><td class="num">${fmt(l.annual)}</td></tr>`).join('')
  + `<tr class="strong"><td>Total</td><td></td><td class="num">${fmt(DATA.annual_benefit)}</td></tr>`;

document.getElementById('sens-tbody').innerHTML = DATA.sensitivity.map(s => {
  const bold = s.key === 'expected' ? 'class="strong"' : '';
  const roi = s.roi_pct != null ? (s.roi_pct + '%') : 'n/a';
  const pb = s.payback_months != null ? (s.payback_months + ' m') : 'n/a';
  const cls = s.net_3yr >= 0 ? 'pos' : 'neg';
  return `<tr ${bold}><td>${esc(s.name)}</td><td class="num">${s.mult}x</td><td class="num">${fmt(s.annual_benefit)}</td><td class="num">${roi}</td><td class="num">${pb}</td><td class="num ${cls}">${fmt(s.net_3yr)}</td></tr>`;
}).join('');

document.getElementById('ty-tbody').innerHTML = DATA.three_year.map(y => {
  const cls = y.net_cumulative >= 0 ? 'pos' : 'neg';
  return `<tr><td>Ano ${y.year}</td><td class="num">${fmt(y.benefit)}</td><td class="num">${fmt(y.cost)}</td><td class="num">${fmt(y.net_year)}</td><td class="num ${cls}"><strong>${fmt(y.net_cumulative)}</strong></td></tr>`;
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

    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=hr-initiative-roi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
