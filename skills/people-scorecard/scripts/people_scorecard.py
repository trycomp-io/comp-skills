#!/usr/bin/env python3
"""
people_scorecard.py — Pacote canônico de People analytics a partir de um
roster CSV (+ opcional CSV de eventos). Gera um scorecard executivo de uma
página: headcount, attrition, tenure, span of control, mobilidade interna,
representatividade (com regra de confidencialidade) e crescimento.

Inputs:
  - Roster CSV (atual): name, area, level, manager (opc), gender (opc),
    tenure_months OU hire_date, salary (opc).
  - Events CSV (opc): type (hire/exit/promotion), date, regretted (opc).

Output: HTML dashboard executivo (tiles + tabelas + tendência se houver datas).

Uso:
    python3 people_scorecard.py --roster roster.csv [--events events.csv]
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "people-scorecard"
SKILL_VERSION = "1.0.0"

MIN_GROUP = 3  # regra de confidencialidade: grupos < 3 são suprimidos


ROSTER_ALIASES = {
    "name":     ["name", "nome", "colaborador", "employee", "funcionario"],
    "area":     ["area", "área", "departamento", "department", "time", "squad"],
    "level":    ["level", "nivel", "nível", "senioridade", "grade", "cargo_nivel"],
    "manager":  ["manager", "gestor", "gerente", "lider", "líder", "reports_to"],
    "gender":   ["gender", "genero", "gênero", "sexo", "sex"],
    "tenure":   ["tenure_months", "tenure", "tempo_de_casa", "meses_de_casa", "meses_casa"],
    "hire_date":["hire_date", "data_admissao", "data_de_admissao", "admissao", "start_date", "data_contratacao"],
    "salary":   ["salary", "salario", "salário", "salario_base"],
}
EVENT_ALIASES = {
    "type":     ["type", "tipo", "event", "evento", "movimento"],
    "date":     ["date", "data", "event_date", "data_evento"],
    "regretted":["regretted", "lamentavel", "lamentável", "regretted_exit", "voluntario_lamentavel"],
    "area":     ["area", "área", "departamento", "department"],
}

# níveis considerados liderança (heurística por substring, ajustável)
LEADER_HINTS = ["lead", "líder", "lider", "head", "manager", "gestor", "gerente",
                "director", "diretor", "vp", "chief", "c-level", "principal", "staff",
                "l5", "l6", "l7", "l8", "senior_manager"]


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
    s = str(v).strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def _truthy(v):
    return _norm(v) in ("1", "true", "sim", "yes", "y", "s", "x")


def parse_date(v):
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y", "%Y-%m"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def norm_gender(v):
    n = _norm(v)
    if n in ("f", "female", "feminino", "fem", "mulher", "w"):
        return "F"
    if n in ("m", "male", "masculino", "masc", "homem"):
        return "M"
    return None


def is_leader(level):
    nl = _norm(level)
    return any(h in nl for h in LEADER_HINTS)


def months_between(d1, d2):
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def analyze(roster, cols_r, events, cols_e):
    now = datetime.now()
    total = len(roster)

    by_area = defaultdict(int)
    by_level = defaultdict(int)
    tenures = []
    by_gender = defaultdict(int)
    leader_gender = defaultdict(int)
    leader_total = 0
    reports_per_mgr = defaultdict(int)
    has_manager_col = bool(cols_r.get("manager"))

    for row in roster:
        area = (row.get(cols_r.get("area") or "") or "—").strip() or "—"
        level = (row.get(cols_r.get("level") or "") or "—").strip() or "—"
        by_area[area] += 1
        by_level[level] += 1

        # tenure
        ten = _f(row.get(cols_r["tenure"])) if cols_r.get("tenure") else None
        if ten is None and cols_r.get("hire_date"):
            d = parse_date(row.get(cols_r["hire_date"]))
            if d:
                ten = months_between(d, now)
        if ten is not None and ten >= 0:
            tenures.append(ten)

        # gender + leadership representation
        if cols_r.get("gender"):
            g = norm_gender(row.get(cols_r["gender"]))
            if g:
                by_gender[g] += 1
                if is_leader(level):
                    leader_total += 1
                    leader_gender[g] += 1

        # span of control
        if has_manager_col:
            mgr = (row.get(cols_r["manager"]) or "").strip()
            if mgr:
                reports_per_mgr[mgr] += 1

    # ---- Headcount ----
    headcount = {
        "total": total,
        "by_area": sorted([{"name": k, "hc": v} for k, v in by_area.items()], key=lambda x: -x["hc"]),
        "by_level": sorted([{"name": k, "hc": v} for k, v in by_level.items()], key=lambda x: -x["hc"]),
    }

    # ---- Tenure ----
    tenure_stats = None
    if tenures:
        buckets = {"0-12m": 0, "12-24m": 0, "24-48m": 0, "48m+": 0}
        for t in tenures:
            if t < 12: buckets["0-12m"] += 1
            elif t < 24: buckets["12-24m"] += 1
            elif t < 48: buckets["24-48m"] += 1
            else: buckets["48m+"] += 1
        tenure_stats = {
            "avg_months": round(statistics.mean(tenures), 1),
            "median_months": round(statistics.median(tenures), 1),
            "distribution": buckets,
        }

    # ---- Span of control ----
    span_stats = None
    if has_manager_col and reports_per_mgr:
        spans = list(reports_per_mgr.values())
        sbuckets = {"1-3": 0, "4-7": 0, "8-12": 0, "13+": 0}
        for s in spans:
            if s <= 3: sbuckets["1-3"] += 1
            elif s <= 7: sbuckets["4-7"] += 1
            elif s <= 12: sbuckets["8-12"] += 1
            else: sbuckets["13+"] += 1
        span_stats = {
            "managers": len(spans),
            "avg_span": round(statistics.mean(spans), 1),
            "max_span": max(spans),
            "distribution": sbuckets,
        }

    # ---- Representatividade (confidencialidade < 3 suprimida) ----
    representation = None
    if by_gender:
        total_gendered = sum(by_gender.values())
        overall = {}
        for g in ("F", "M"):
            c = by_gender.get(g, 0)
            overall[g] = {"count": c if c >= MIN_GROUP else None,
                          "pct": round(c / total_gendered * 100, 1) if (c >= MIN_GROUP and total_gendered) else None}
        leadership = None
        if leader_total >= MIN_GROUP:
            leadership = {}
            for g in ("F", "M"):
                c = leader_gender.get(g, 0)
                leadership[g] = {"count": c if c >= MIN_GROUP else None,
                                 "pct": round(c / leader_total * 100, 1) if (c >= MIN_GROUP and leader_total) else None}
        representation = {
            "overall": overall, "total_gendered": total_gendered,
            "leadership": leadership, "leader_total": leader_total if leader_total >= MIN_GROUP else None,
            "suppressed": any(by_gender.get(g, 0) < MIN_GROUP and by_gender.get(g, 0) > 0 for g in ("F", "M")),
        }

    # ---- Eventos: attrition, mobilidade, crescimento, tendência ----
    flows = None
    trend = None
    if events is not None and cols_e.get("type"):
        hires = exits = promos = regretted_exits = 0
        dated_exits = []
        monthly = defaultdict(lambda: {"hire": 0, "exit": 0, "promotion": 0})
        for ev in events:
            t = _norm(ev.get(cols_e["type"]))
            d = parse_date(ev.get(cols_e["date"])) if cols_e.get("date") else None
            key = d.strftime("%Y-%m") if d else None
            if t in ("hire", "contratacao", "admissao", "admission"):
                hires += 1
                if key: monthly[key]["hire"] += 1
            elif t in ("exit", "desligamento", "saida", "termination", "exit_voluntario"):
                exits += 1
                if key:
                    monthly[key]["exit"] += 1
                    dated_exits.append(d)
                if cols_e.get("regretted") and _truthy(ev.get(cols_e["regretted"])):
                    regretted_exits += 1
            elif t in ("promotion", "promocao", "promoção", "promo"):
                promos += 1
                if key: monthly[key]["promotion"] += 1

        # avg headcount: aproxima por headcount atual + metade do fluxo líquido
        avg_hc = total + (exits - hires) / 2 if total else total
        avg_hc = max(avg_hc, 1)
        # janela do período pelos eventos datados (default 12m)
        period_months = 12
        all_dates = [parse_date(ev.get(cols_e["date"])) for ev in events if cols_e.get("date")]
        all_dates = [d for d in all_dates if d]
        if len(all_dates) >= 2:
            span_m = months_between(min(all_dates), max(all_dates)) + 1
            period_months = max(1, span_m)
        annualize = 12 / period_months
        flows = {
            "hires": hires, "exits": exits, "promotions": promos,
            "regretted_exits": regretted_exits,
            "period_months": period_months,
            "attrition_rate": round(exits / avg_hc * annualize * 100, 1),
            "regretted_rate": round(regretted_exits / avg_hc * annualize * 100, 1) if cols_e.get("regretted") else None,
            "internal_mobility_rate": round(promos / total * 100, 1) if total else 0,
            "growth_rate": round((hires - exits) / total * 100, 1) if total else 0,
            "new_hire_rate": round(hires / total * 100, 1) if total else 0,
        }
        if monthly:
            trend = [{"month": k, **monthly[k]} for k in sorted(monthly)]

    # ---- Insights ----
    insights = []
    insights.append(f"Headcount atual: <strong>{total}</strong> em {len(by_area)} área(s) e {len(by_level)} nível(is).")
    if tenure_stats:
        insights.append(f"Tenure médio: <strong>{tenure_stats['avg_months']} meses</strong> (mediana {tenure_stats['median_months']}).")
    if span_stats:
        insights.append(f"Span of control médio: <strong>{span_stats['avg_span']}</strong> reportes por gestor (máx {span_stats['max_span']}).")
    if flows:
        insights.append(f"Attrition anualizada: <strong>{flows['attrition_rate']}%</strong>"
                        + (f" (lamentável {flows['regretted_rate']}%)" if flows['regretted_rate'] is not None else "")
                        + f" · mobilidade interna {flows['internal_mobility_rate']}% · crescimento {flows['growth_rate']}%.")
    if representation and representation["overall"].get("F", {}).get("pct") is not None:
        msg = f"Representatividade feminina geral: <strong>{representation['overall']['F']['pct']}%</strong>"
        if representation.get("leadership") and representation["leadership"].get("F", {}).get("pct") is not None:
            msg += f" · em liderança: <strong>{representation['leadership']['F']['pct']}%</strong>"
        insights.append(msg + ".")
    if representation and representation.get("suppressed"):
        insights.append("Alguns grupos de gênero foram suprimidos por terem menos de 3 pessoas (regra de confidencialidade).")

    return {
        "summary": {
            "headcount": total,
            "areas": len(by_area),
            "levels": len(by_level),
            "attrition_rate": flows["attrition_rate"] if flows else None,
            "internal_mobility_rate": flows["internal_mobility_rate"] if flows else None,
            "avg_tenure": tenure_stats["avg_months"] if tenure_stats else None,
            "avg_span": span_stats["avg_span"] if span_stats else None,
        },
        "headcount": headcount,
        "tenure": tenure_stats,
        "span": span_stats,
        "representation": representation,
        "flows": flows,
        "trend": trend,
        "insights": insights,
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>People scorecard · Zivo</title>
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
@media (min-width:561px){.stat-grid.six{grid-template-columns:repeat(auto-fit,minmax(160px,1fr))}}
.section > .grid-2 + .grid-2{margin-top:48px}
.rep-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:24px}
.rep-grid h3{margin-bottom:8px}
</style></head>
<body>

<header class="hero">
<div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>People scorecard</span><span id="generated"></span><span>Confidencial</span></div>
<h1>Pacote mensal de People analytics</h1>
<p class="hero-sub">Headcount, attrition, mobilidade, tenure, span of control e representatividade num só lugar.</p>
</div>
</header>

<main class="page">

<section class="section">
<div class="stat-grid six" id="tiles"></div>
</section>

<section class="section" id="insights-card" style="display:none;">
<h2>Resumo</h2>
<div class="card"><ul class="insights" id="insights-list"></ul></div>
</section>

<section class="section">
<div class="grid-2">
<div><h2>Headcount por área</h2><div class="card table-wrap"><table><thead><tr><th>Área</th><th class="num">HC</th><th class="num">%</th></tr></thead><tbody id="area-tbody"></tbody></table></div></div>
<div><h2>Headcount por nível</h2><div class="card table-wrap"><table><thead><tr><th>Nível</th><th class="num">HC</th><th class="num">%</th></tr></thead><tbody id="level-tbody"></tbody></table></div></div>
</div>
<div class="grid-2">
<div id="tenure-card"><h2>Distribuição de tenure</h2><div class="card table-wrap"><table><thead><tr><th>Faixa</th><th class="num">HC</th></tr></thead><tbody id="tenure-tbody"></tbody></table></div></div>
<div id="span-card"><h2>Span of control</h2><div class="card table-wrap"><table><thead><tr><th>Reportes</th><th class="num">Gestores</th></tr></thead><tbody id="span-tbody"></tbody></table></div></div>
</div>
</section>

<section class="section" id="rep-card" style="display:none;">
<h2>Representatividade de gênero</h2>
<p class="section-sub">Grupos com menos de 3 pessoas são suprimidos (—) por confidencialidade.</p>
<div class="card"><div class="rep-grid" id="rep-body"></div></div>
</section>

<section class="section" id="trend-card" style="display:none;">
<h2>Tendência do período</h2>
<div class="card table-wrap"><table><thead><tr><th>Mês</th><th class="num">Contratações</th><th class="num">Saídas</th><th class="num">Promoções</th></tr></thead><tbody id="trend-tbody"></tbody></table></div>
</section>

</main>

<footer class="site-footer">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=people-scorecard" aria-label="Zivo"><svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg></a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'short', year:'numeric' });
const pct = (n, d) => d ? (n / d * 100).toFixed(1) + '%' : '—';

const s = DATA.summary;
const tiles = [
  { label: 'Headcount', value: s.headcount },
  { label: 'Áreas', value: s.areas },
  { label: 'Attrition anual.', value: s.attrition_rate != null ? s.attrition_rate + '%' : '—', accent: true },
  { label: 'Mobilidade interna', value: s.internal_mobility_rate != null ? s.internal_mobility_rate + '%' : '—' },
  { label: 'Tenure médio (m)', value: s.avg_tenure != null ? s.avg_tenure : '—' },
  { label: 'Span médio', value: s.avg_span != null ? s.avg_span : '—' },
];
document.getElementById('tiles').innerHTML = tiles.map(t =>
  `<div class="stat-card"><div class="label">${t.label}</div><div class="value${t.accent ? ' accent' : ''}">${t.value}</div></div>`).join('');

if (DATA.insights.length) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li><i class="zv-dot"></i><span>${i}</span></li>`).join('');
}

document.getElementById('area-tbody').innerHTML = DATA.headcount.by_area.map(a =>
  `<tr><td><strong>${esc(a.name)}</strong></td><td class="num">${a.hc}</td><td class="num">${pct(a.hc, s.headcount)}</td></tr>`).join('');
document.getElementById('level-tbody').innerHTML = DATA.headcount.by_level.map(l =>
  `<tr><td><strong>${esc(l.name)}</strong></td><td class="num">${l.hc}</td><td class="num">${pct(l.hc, s.headcount)}</td></tr>`).join('');

if (DATA.tenure) {
  document.getElementById('tenure-tbody').innerHTML = Object.entries(DATA.tenure.distribution).map(([k, v]) =>
    `<tr><td>${esc(k)}</td><td class="num">${v}</td></tr>`).join('');
} else { document.getElementById('tenure-card').style.display = 'none'; }

if (DATA.span) {
  document.getElementById('span-tbody').innerHTML = Object.entries(DATA.span.distribution).map(([k, v]) =>
    `<tr><td>${esc(k)} reportes</td><td class="num">${v}</td></tr>`).join('');
} else { document.getElementById('span-card').style.display = 'none'; }

if (DATA.representation) {
  const r = DATA.representation;
  const blk = (title, obj, tot) => {
    if (!obj) return `<div><h3>${title}</h3><p class="small muted">Grupo total &lt; 3, suprimido por confidencialidade.</p></div>`;
    const rows = ['F','M'].map(g => {
      const c = obj[g] && obj[g].count != null ? obj[g].count : '—';
      const p = obj[g] && obj[g].pct != null ? obj[g].pct + '%' : '—';
      return `<tr><td>${g === 'F' ? 'Feminino' : 'Masculino'}</td><td class="num">${c}</td><td class="num">${p}</td></tr>`;
    }).join('');
    return `<div><h3>${title}${tot ? ' (n=' + tot + ')' : ''}</h3><div class="table-wrap"><table><thead><tr><th>Gênero</th><th class="num">HC</th><th class="num">%</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
  };
  document.getElementById('rep-card').style.display = '';
  document.getElementById('rep-body').innerHTML =
    blk('Geral', r.overall, r.total_gendered) + blk('Liderança', r.leadership, r.leader_total);
}

if (DATA.trend && DATA.trend.length) {
  document.getElementById('trend-card').style.display = '';
  document.getElementById('trend-tbody').innerHTML = DATA.trend.map(m =>
    `<tr><td><strong>${esc(m.month)}</strong></td><td class="num">${m.hire}</td><td class="num">${m.exit}</td><td class="num">${m.promotion}</td></tr>`).join('');
}
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="People scorecard executivo a partir de um roster CSV (+ eventos opcional).")
    p.add_argument("--roster", type=Path, required=True)
    p.add_argument("--events", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    headers_r, roster = load_csv(args.roster)
    cols_r = {k: auto_detect(headers_r, ROSTER_ALIASES, k) for k in ROSTER_ALIASES}
    if not roster:
        sys.exit("Roster vazio.")

    events, cols_e = None, {}
    if args.events:
        headers_e, events = load_csv(args.events)
        cols_e = {k: auto_detect(headers_e, EVENT_ALIASES, k) for k in EVENT_ALIASES}
        if not cols_e.get("type"):
            print("Aviso: events CSV sem coluna 'type' reconhecida — taxas e tendência serão omitidas.")
            events = None

    print(f"Roster: {len(roster)} | colunas: " + ", ".join(f"{k}={v}" for k, v in cols_r.items() if v))
    if events is not None:
        print(f"Eventos: {len(events)}")
    data = analyze(roster, cols_r, events, cols_e)
    out = args.output or Path.cwd() / f"people-scorecard-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    line = f"  HC {data['summary']['headcount']}"
    if data['summary']['attrition_rate'] is not None:
        line += f" | attrition {data['summary']['attrition_rate']}%"
    if data['summary']['avg_tenure'] is not None:
        line += f" | tenure médio {data['summary']['avg_tenure']}m"
    print(line)

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=people-scorecard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
