#!/usr/bin/env python3
"""
manager_scorecard.py — Diagnóstico de eficácia por gestor cruzando múltiplos
sinais (span, atrito do time, engajamento médio, taxa de promoção) num score
composto 0-100 com bandas e flags acionáveis.

Inputs:
  - Roster CSV: name, manager (mínimo). Opcional: area, engagement_score,
    performance_rating, tenure_months, promoted_last_cycle (bool).
  - Events CSV (opcional): manager, type (exit), regretted (bool).

Output: HTML executivo com ranking de gestores, scorecard por gestor,
distribuição de bandas e outliers.

Uso:
    python3 manager_scorecard.py --roster roster.csv
    python3 manager_scorecard.py --roster roster.csv --events exits.csv
"""

from __future__ import annotations

import argparse
import csv
import json
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

SKILL_NAME = "manager-effectiveness-scorecard"
SKILL_VERSION = "1.0.0"

MIN_DIRECTS = 3  # confidencialidade: gestores com <3 directs viram "amostra pequena"

ROSTER_ALIASES = {
    "name":        ["name", "nome", "colaborador", "employee"],
    "manager":     ["manager", "gestor", "gerente", "lider", "líder", "reports_to", "manager_name"],
    "area":        ["area", "área", "departamento", "department", "time", "squad"],
    "engagement":  ["engagement_score", "engagement", "engajamento", "enps", "score_engajamento"],
    "performance": ["performance_rating", "performance", "desempenho", "rating", "nota"],
    "tenure":      ["tenure_months", "tenure", "tempo_casa", "meses_casa", "tempo_de_casa"],
    "promoted":    ["promoted_last_cycle", "promoted", "promovido", "promocao", "promoção"],
}
EVENT_ALIASES = {
    "manager":   ["manager", "gestor", "gerente", "lider", "líder", "reports_to"],
    "type":      ["type", "tipo", "event_type", "evento"],
    "regretted": ["regretted", "regret", "lamentavel", "lamentável", "regrettable"],
}


def _norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").strip().lower().replace(" ", "_")


def auto_detect(headers, aliases, key):
    h = {_norm(x): x for x in headers}
    for cand in aliases[key]:
        if _norm(cand) in h:
            return h[_norm(cand)]
    return None


def _f(v):
    if v is None or v == "":
        return None
    s = str(v).strip().replace("%", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _bool(v):
    if v is None:
        return False
    return _norm(str(v)) in ("1", "true", "sim", "yes", "y", "s", "verdadeiro", "promovido")


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def band(score):
    if score is None:
        return "n/a"
    if score < 40:
        return "at-risk"
    if score < 60:
        return "developing"
    if score < 80:
        return "solid"
    return "exemplar"


def normalize_engagement(values):
    """Detecta escala (0-5, 0-10 ou 0-100) e retorna média em 0-100."""
    if not values:
        return None
    mx = max(values)
    if mx <= 5:
        scale = 5
    elif mx <= 10:
        scale = 10
    else:
        scale = 100
    return round(sum(values) / len(values) / scale * 100, 1)


def analyze(roster, cols_r, events, cols_e):
    # agrupa exits por gestor
    exits_by_mgr = defaultdict(lambda: {"total": 0, "regretted": 0})
    has_regretted = bool(cols_e.get("regretted")) if cols_e else False
    for e in (events or []):
        typ = _norm(e.get(cols_e.get("type") or "", "")) if cols_e.get("type") else "exit"
        if cols_e.get("type") and "exit" not in typ and "sai" not in typ and "deslig" not in typ:
            continue
        mgr = (e.get(cols_e.get("manager") or "") or "").strip()
        if not mgr:
            continue
        exits_by_mgr[mgr]["total"] += 1
        if has_regretted and _bool(e.get(cols_e["regretted"])):
            exits_by_mgr[mgr]["regretted"] += 1

    teams = defaultdict(list)
    for row in roster:
        mgr = (row.get(cols_r.get("manager") or "") or "").strip()
        if not mgr:
            continue
        teams[mgr].append(row)

    scorecards = []
    has_eng = bool(cols_r.get("engagement"))
    has_promo = bool(cols_r.get("promoted"))
    has_exits = bool(events)

    for mgr, directs in teams.items():
        span = len(directs)
        eng_vals = []
        if has_eng:
            for d in directs:
                v = _f(d.get(cols_r["engagement"]))
                if v is not None:
                    eng_vals.append(v)
        team_eng = normalize_engagement(eng_vals)  # 0-100 ou None

        promo_count = 0
        if has_promo:
            promo_count = sum(1 for d in directs if _bool(d.get(cols_r["promoted"])))
        promo_rate = round(promo_count / span * 100, 1) if (has_promo and span) else None

        ex = exits_by_mgr.get(mgr, {"total": 0, "regretted": 0})
        # atrito = saídas / (time atual + saídas) — denominador aproxima headcount do período
        denom = span + ex["total"]
        attrition = round(ex["total"] / denom * 100, 1) if (has_exits and denom) else None
        reg_attrition = round(ex["regretted"] / denom * 100, 1) if (has_exits and has_regretted and denom) else None
        # para score: usa regretted se disponível, senão total
        attrition_for_score = reg_attrition if reg_attrition is not None else attrition

        # ---- score composto 0-100 (blend transparente dos sinais disponíveis) ----
        comps = []  # (peso, valor 0-100)
        if team_eng is not None:
            comps.append((0.40, team_eng))
        if attrition_for_score is not None:
            # inverso: 0% atrito = 100; >=40% atrito = 0
            inv = max(0.0, min(100.0, 100 - attrition_for_score / 40 * 100))
            comps.append((0.30, round(inv, 1)))
        if promo_rate is not None:
            # 0% = 0; >=25% promo já é saudável = 100
            ps = max(0.0, min(100.0, promo_rate / 25 * 100))
            comps.append((0.15, round(ps, 1)))
        # span health: ideal 4-8; penaliza overloaded e underutilized
        if span >= 9:
            sh = max(0.0, 100 - (span - 8) * 8)
        elif span <= 3:
            sh = 50.0
        else:
            sh = 100.0
        comps.append((0.15, sh))

        wsum = sum(w for w, _ in comps)
        score = round(sum(w * v for w, v in comps) / wsum, 1) if wsum else None

        small_sample = span < MIN_DIRECTS

        flags = []
        if attrition_for_score is not None and attrition_for_score >= 20 and team_eng is not None and team_eng < 60:
            flags.append({"k": "at_risk", "label": "Gestor em risco — atrito alto + engajamento baixo"})
        if span > 12 and team_eng is not None and team_eng < 60:
            flags.append({"k": "overloaded", "label": "Sobrecarregado — span >12 com engajamento baixo"})
        elif span > 12:
            flags.append({"k": "overloaded", "label": "Span amplo (>12) — monitorar capacidade"})
        if 1 <= span <= 3:
            flags.append({"k": "underutilized", "label": "Subutilizado — span de 1 a 3 directs"})

        scorecards.append({
            "manager": mgr,
            "span": span,
            "team_engagement": team_eng,
            "attrition": attrition,
            "regretted_attrition": reg_attrition,
            "promo_rate": promo_rate,
            "promo_count": promo_count if has_promo else None,
            "score": score,
            "band": band(score) if not small_sample else "small",
            "small_sample": small_sample,
            "flags": flags,
            "components": [{"w": w, "v": v} for w, v in comps],
        })

    # rankings excluem amostra pequena
    ranked = sorted(
        [s for s in scorecards if not s["small_sample"] and s["score"] is not None],
        key=lambda s: -s["score"],
    )
    small = [s for s in scorecards if s["small_sample"]]

    distribution = defaultdict(int)
    for s in ranked:
        distribution[s["band"]] += 1

    scores_only = [s["score"] for s in ranked if s["score"] is not None]
    avg_score = round(sum(scores_only) / len(scores_only), 1) if scores_only else None

    at_risk = [s for s in ranked if s["band"] == "at-risk"]
    exemplar = [s for s in ranked if s["band"] == "exemplar"]

    insights = []
    if not ranked:
        insights.append("Nenhum gestor com 3+ directs pôde ser ranqueado — verifique a coluna de gestor no roster.")
    else:
        insights.append(f"<strong>{len(ranked)}</strong> gestores ranqueados (amostra ≥{MIN_DIRECTS} directs). Score médio: <strong>{avg_score}</strong>.")
        if exemplar:
            insights.append(f"<strong>{len(exemplar)}</strong> exemplar(es) — referências de práticas de gestão a escalar.")
        if at_risk:
            insights.append(f"<strong>{len(at_risk)}</strong> gestor(es) em risco (score <40) — priorizar conversa de desenvolvimento.")
        n_over = sum(1 for s in scorecards if any(f["k"] == "overloaded" for f in s["flags"]))
        n_under = sum(1 for s in scorecards if any(f["k"] == "underutilized" for f in s["flags"]))
        if n_over:
            insights.append(f"<strong>{n_over}</strong> gestor(es) sobrecarregado(s) (span amplo) — avaliar redistribuição de times.")
        if n_under:
            insights.append(f"<strong>{n_under}</strong> gestor(es) subutilizado(s) (1-3 directs) — oportunidade de consolidar camadas.")
        if small:
            insights.append(f"<strong>{len(small)}</strong> gestor(es) com amostra pequena (&lt;{MIN_DIRECTS} directs) exibidos sem ranking, por confidencialidade.")

    return {
        "summary": {
            "managers_ranked": len(ranked),
            "managers_total": len(scorecards),
            "small_sample": len(small),
            "avg_score": avg_score,
            "has_engagement": has_eng,
            "has_exits": has_exits,
            "has_promo": has_promo,
        },
        "distribution": {k: distribution[k] for k in ("at-risk", "developing", "solid", "exemplar")},
        "ranked": ranked,
        "small": small,
        "insights": insights,
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manager effectiveness scorecard · Zivo</title>
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
.flags{display:flex;flex-wrap:wrap;gap:4px}
</style></head>
<body>

<header class="hero">
<div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>Manager effectiveness</span><span id="generated"></span><span>Confidencial</span></div>
<h1>Eficácia por gestor</h1>
<p class="hero-sub">Score composto de engajamento do time, atrito e promoções, com flags por gestor.</p>
</div>
</header>

<main class="page">

<section class="section">
<div class="stat-grid">
<div class="stat-card"><div class="label">Gestores ranqueados</div><div class="value" id="s-ranked"></div><div class="context">Com 3 ou mais directs.</div></div>
<div class="stat-card"><div class="label">Total de gestores</div><div class="value" id="s-total"></div><div class="context">No roster enviado.</div></div>
<div class="stat-card"><div class="label">Score médio</div><div class="value accent" id="s-avg"></div><div class="context">Escala de 0 a 100.</div></div>
<div class="stat-card"><div class="label">Amostra pequena</div><div class="value" id="s-small"></div><div class="context">Fora do ranking.</div></div>
</div>
</section>

<section class="section">
<h2>Distribuição por banda</h2>
<div class="stat-grid" id="dist"></div>
</section>

<section class="section" id="insights-card" style="display:none;">
<h2>Insights</h2>
<div class="card"><ul class="insights" id="insights-list"></ul></div>
</section>

<section class="section">
<h2>Ranking de gestores</h2>
<div class="card table-wrap"><table><thead><tr><th class="num">#</th><th>Gestor</th><th>Banda</th><th class="num">Score</th><th class="num">Span</th><th class="num">Engaj.</th><th class="num">Atrito</th><th class="num">Promo</th><th>Flags</th></tr></thead><tbody id="rank-tbody"></tbody></table></div>
</section>

<section class="section" id="small-card" style="display:none;">
<h2>Amostra pequena (sem ranking)</h2>
<p class="section-sub">Gestores com menos de 3 directs. Exibidos por contexto, fora de rankings e médias, por confidencialidade.</p>
<div class="card table-wrap"><table><thead><tr><th>Gestor</th><th class="num">Span</th><th class="num">Engaj.</th><th class="num">Atrito</th><th class="num">Promo</th><th>Flags</th></tr></thead><tbody id="small-tbody"></tbody></table></div>
</section>

</main>

<footer class="site-footer">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=manager-effectiveness-scorecard" aria-label="Zivo"><svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg></a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'short', year:'numeric' });
const pct = v => (v === null || v === undefined) ? '—' : v + '%';
const num = v => (v === null || v === undefined) ? '—' : v;

document.getElementById('s-ranked').textContent = DATA.summary.managers_ranked;
document.getElementById('s-total').textContent = DATA.summary.managers_total;
document.getElementById('s-avg').textContent = num(DATA.summary.avg_score);
document.getElementById('s-small').textContent = DATA.summary.small_sample;

const bandLabels = { 'at-risk':'At-risk (<40)', developing:'Developing (40-59)', solid:'Solid (60-79)', exemplar:'Exemplar (80+)' };
const bandClass = { 'at-risk':'badge-bad', developing:'badge-warn', solid:'badge-info', exemplar:'badge-good', small:'' };
document.getElementById('dist').innerHTML = ['at-risk','developing','solid','exemplar'].map(k =>
  `<div class="stat-card">
    <div class="label">${bandLabels[k]}</div>
    <div class="value">${DATA.distribution[k] || 0}</div>
    <div class="context"><span class="badge ${bandClass[k]}">${k}</span></div>
  </div>`).join('');

if (DATA.insights.length > 0) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li><i class="zv-dot"></i><span>${i}</span></li>`).join('');
}

const flagsHtml = fl => fl.length ? '<div class="flags">' + fl.map(f => `<span class="badge badge-warn">${esc(f.label)}</span>`).join('') + '</div>' : '<span class="muted">—</span>';
const bandPill = b => `<span class="badge ${bandClass[b]}">${b === 'small' ? 'amostra pequena' : b}</span>`;

document.getElementById('rank-tbody').innerHTML = DATA.ranked.map((s, i) =>
  `<tr><td class="num">${i+1}</td><td><strong>${esc(s.manager)}</strong></td><td>${bandPill(s.band)}</td><td class="num"><strong>${num(s.score)}</strong></td><td class="num">${s.span}</td><td class="num">${pct(s.team_engagement)}</td><td class="num">${pct(s.regretted_attrition !== null ? s.regretted_attrition : s.attrition)}</td><td class="num">${pct(s.promo_rate)}</td><td>${flagsHtml(s.flags)}</td></tr>`).join('');

if (DATA.small.length > 0) {
  document.getElementById('small-card').style.display = '';
  document.getElementById('small-tbody').innerHTML = DATA.small.map(s =>
    `<tr><td><strong>${esc(s.manager)}</strong></td><td class="num">${s.span}</td><td class="num">${pct(s.team_engagement)}</td><td class="num">${pct(s.regretted_attrition !== null ? s.regretted_attrition : s.attrition)}</td><td class="num">${pct(s.promo_rate)}</td><td>${flagsHtml(s.flags)}</td></tr>`).join('');
}
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Scorecard de eficácia de gestores.")
    p.add_argument("--roster", type=Path, required=True)
    p.add_argument("--events", type=Path, help="CSV opcional de saídas (manager, type, regretted)")
    p.add_argument("--output", type=Path)
    p.add_argument("--manager-col"); p.add_argument("--engagement-col")
    p.add_argument("--promoted-col")
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    headers_r, roster = load_csv(args.roster)
    cols_r = {k: auto_detect(headers_r, ROSTER_ALIASES, k) for k in ROSTER_ALIASES}
    if args.manager_col: cols_r["manager"] = args.manager_col
    if args.engagement_col: cols_r["engagement"] = args.engagement_col
    if args.promoted_col: cols_r["promoted"] = args.promoted_col
    if not cols_r.get("manager"):
        sys.exit("Roster precisa de uma coluna de gestor (manager). Verifique colunas.")

    events, cols_e = [], {}
    if args.events:
        headers_e, events = load_csv(args.events)
        cols_e = {k: auto_detect(headers_e, EVENT_ALIASES, k) for k in EVENT_ALIASES}
        if not cols_e.get("manager"):
            sys.exit("Events CSV precisa de coluna de gestor (manager).")

    print(f"Roster: {len(roster)} linhas | Events: {len(events)} | gestor='{cols_r.get('manager')}'")
    data = analyze(roster, cols_r, events, cols_e)
    out = args.output or Path.cwd() / f"manager-scorecard-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    print(f"  {data['summary']['managers_ranked']} gestores ranqueados | score médio: {data['summary']['avg_score']}")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=manager-effectiveness-scorecard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
