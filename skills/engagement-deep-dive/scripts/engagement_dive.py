#!/usr/bin/env python3
"""
engagement_dive.py — Analisa resultados de pesquisa de engajamento (eNPS,
survey de cultura, pulse) e segmenta por tenure / área / manager / nível.

Input CSV: score (obrigatório, 0-10 ou 1-5), + dimensões opcionais (area,
tenure_months, manager_id, level, recommended_to_friend (eNPS-style)).

Output: HTML executivo com eNPS global, segmentação, áreas críticas,
correlações tentativas, recomendações.

Uso:
    python3 engagement_dive.py --input survey.csv
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

SKILL_NAME = "engagement-deep-dive"
SKILL_VERSION = "1.0.0"


ALIASES = {
    "score":       ["score", "nota", "rating", "satisfaction"],
    "enps":        ["enps", "nps", "recommend", "recomendar", "recommended", "recommended_to_friend"],
    "area":        ["area", "área", "departamento", "department"],
    "level":       ["level", "nivel", "nível", "senioridade"],
    "tenure_months": ["tenure_months", "tenure", "tempo_casa", "tempo_meses"],
    "manager_id":  ["manager_id", "manager", "gestor", "gestor_id"],
}


def _esc(v):
    import html
    return html.escape(str(v), quote=True) if v is not None else ""


def _norm(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii").strip().lower().replace(" ", "_")


def auto_detect(headers, key):
    h = {_norm(x): x for x in headers}
    for c in ALIASES[key]:
        if _norm(c) in h:
            return h[_norm(c)]
    return None


def _f(v):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def tenure_band(m):
    if m is None: return "Desconhecido"
    if m < 6: return "0-6m"
    if m < 12: return "6-12m"
    if m < 24: return "1-2y"
    if m < 36: return "2-3y"
    if m < 60: return "3-5y"
    return "5y+"


def enps_classify(score):
    """eNPS-style 0-10: promoter 9-10, passive 7-8, detractor 0-6."""
    if score is None: return None
    if score >= 9: return "promoter"
    if score >= 7: return "passive"
    return "detractor"


def calc_enps(items):
    """eNPS = % promoters - % detractors."""
    if not items: return None
    n = len(items)
    p = sum(1 for x in items if x == "promoter")
    d = sum(1 for x in items if x == "detractor")
    return round((p - d) / n * 100, 1)


def analyze(rows, cols):
    overall_scores = []
    overall_enps_classes = []
    by_area = defaultdict(list)
    by_area_enps = defaultdict(list)
    by_tenure = defaultdict(list)
    by_level = defaultdict(list)
    by_manager = defaultdict(list)
    has_enps = bool(cols.get("enps"))

    for row in rows:
        if cols.get("score"):
            s = _f(row.get(cols["score"]))
            if s is not None:
                overall_scores.append(s)
        if has_enps:
            e = _f(row.get(cols["enps"]))
            cls = enps_classify(e)
            if cls is not None:
                overall_enps_classes.append(cls)

        area = (row.get(cols.get("area") or "") or "—").strip() if cols.get("area") else "—"
        if cols.get("score"):
            s = _f(row.get(cols["score"]))
            if s is not None:
                by_area[area].append(s)
        if has_enps:
            e = _f(row.get(cols["enps"]))
            cls = enps_classify(e)
            if cls is not None:
                by_area_enps[area].append(cls)

        tenure = _f(row.get(cols.get("tenure_months") or "")) if cols.get("tenure_months") else None
        tb = tenure_band(tenure)
        if cols.get("score"):
            s = _f(row.get(cols["score"]))
            if s is not None:
                by_tenure[tb].append(s)

        level = (row.get(cols.get("level") or "") or "—").strip() if cols.get("level") else "—"
        if cols.get("score"):
            s = _f(row.get(cols["score"]))
            if s is not None:
                by_level[level].append(s)

        manager = (row.get(cols.get("manager_id") or "") or "").strip() if cols.get("manager_id") else ""
        if manager and cols.get("score"):
            s = _f(row.get(cols["score"]))
            if s is not None:
                by_manager[manager].append(s)

    overall_score = round(statistics.mean(overall_scores), 2) if overall_scores else None
    overall_enps = calc_enps(overall_enps_classes) if overall_enps_classes else None
    n_responses = len(overall_scores) or len(overall_enps_classes)

    def make_rows(d, segment_label):
        rows = []
        for k, scores in d.items():
            if len(scores) < 3:
                continue
            rows.append({
                "segment": k,
                "n": len(scores),
                "avg_score": round(statistics.mean(scores), 2),
                "min_score": round(min(scores), 2),
                "max_score": round(max(scores), 2),
            })
        rows.sort(key=lambda x: x["avg_score"])
        return rows

    area_rows = make_rows(by_area, "area")
    tenure_rows = make_rows(by_tenure, "tenure")
    level_rows = make_rows(by_level, "level")
    bottom_managers = []
    if by_manager:
        bottom_managers = sorted(
            [{"manager": k, "n": len(v), "avg_score": round(statistics.mean(v), 2)}
             for k, v in by_manager.items() if len(v) >= 3],
            key=lambda x: x["avg_score"]
        )[:10]

    insights = []
    if overall_enps is not None:
        if overall_enps < 0:
            insights.append(f"<strong>eNPS negativo ({overall_enps})</strong> — mais detractors que promoters. Crítico.")
        elif overall_enps < 30:
            insights.append(f"eNPS abaixo de benchmarks (atual {overall_enps}; benchmark saudável >30). Identifique áreas/gestores drivers.")
        else:
            insights.append(f"eNPS saudável ({overall_enps}). Continue investigando bolsões com score baixo.")
    if area_rows and overall_score:
        worst_area = area_rows[0]
        if worst_area["avg_score"] < overall_score - 1.0:
            insights.append(f"Área <strong>{_esc(worst_area['segment'])}</strong> ({worst_area['avg_score']}) muito abaixo da média ({overall_score}). Foco prioritário.")
    if tenure_rows:
        if tenure_rows[0]["segment"] in ("0-6m", "6-12m"):
            insights.append(f"Primeiro ano em queda — sinal de problema em onboarding/expectations.")
    if bottom_managers and len(bottom_managers) > 0:
        worst_mgr = bottom_managers[0]
        if overall_score and worst_mgr["avg_score"] < overall_score - 1.5:
            insights.append(f"Gestor <strong>{_esc(worst_mgr['manager'])}</strong> com média {worst_mgr['avg_score']} ({worst_mgr['n']} respostas) — abaixo significativamente da empresa.")

    return {
        "summary": {
            "n_responses": n_responses,
            "overall_score": overall_score,
            "overall_enps": overall_enps,
            "has_enps": has_enps,
        },
        "by_area": area_rows,
        "by_tenure": tenure_rows,
        "by_level": level_rows,
        "bottom_managers": bottom_managers,
        "insights": insights,
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Engagement deep dive · Zivo</title>
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
.score-bad{color:var(--zivo-error);font-weight:700}
.score-med{color:var(--zivo-warning)}
.score-good{color:var(--zivo-success)}
</style></head>
<body>

<header class="hero">
<div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>Engajamento</span><span id="generated"></span><span>Confidencial</span></div>
<h1>Análise de engajamento por segmento</h1>
<p class="hero-sub">Score e eNPS por área, tempo de casa, nível e gestor, com os piores segmentos primeiro.</p>
</div>
</header>

<main class="page">

<section class="section">
<div class="stat-grid">
<div class="stat-card"><div class="label">Respostas</div><div class="value" id="s-n"></div><div class="context">Respostas válidas na pesquisa.</div></div>
<div class="stat-card"><div class="label">Score médio</div><div class="value" id="s-score"></div><div class="context">Média geral de engajamento.</div></div>
<div class="stat-card"><div class="label">eNPS</div><div class="value" id="s-enps"></div><div class="context">Promotores menos detratores.</div></div>
</div>
</section>

<section class="section" id="insights-card" style="display:none;">
<h2>Insights</h2>
<div class="card"><ul class="insights" id="insights-list"></ul></div>
</section>

<section class="section">
<div class="grid-2">
<div><h2>Por área</h2><p class="section-sub">Ordenado: piores primeiro.</p><div class="card table-wrap"><table><thead><tr><th>Área</th><th class="num">N</th><th class="num">Score</th><th class="num">Min</th><th class="num">Max</th></tr></thead><tbody id="area-tbody"></tbody></table></div></div>
<div><h2>Por tempo de casa</h2><p class="section-sub">Faixas de tenure.</p><div class="card table-wrap"><table><thead><tr><th>Faixa</th><th class="num">N</th><th class="num">Score</th><th class="num">Min</th><th class="num">Max</th></tr></thead><tbody id="tenure-tbody"></tbody></table></div></div>
<div><h2>Por nível</h2><p class="section-sub">Senioridade.</p><div class="card table-wrap"><table><thead><tr><th>Nível</th><th class="num">N</th><th class="num">Score</th><th class="num">Min</th><th class="num">Max</th></tr></thead><tbody id="lvl-tbody"></tbody></table></div></div>
<div><h2>Bottom 10 gestores</h2><p class="section-sub">Menor score médio do time.</p><div class="card table-wrap"><table><thead><tr><th>Gestor</th><th class="num">N</th><th class="num">Score</th></tr></thead><tbody id="mgr-tbody"></tbody></table></div></div>
</div>
</section>

</main>

<footer class="site-footer">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=engagement-deep-dive" aria-label="Zivo"><svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg></a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'short', year:'numeric' });
document.getElementById('s-n').textContent = DATA.summary.n_responses;
document.getElementById('s-score').textContent = DATA.summary.overall_score !== null ? DATA.summary.overall_score : '—';
const enpsEl = document.getElementById('s-enps');
const e = DATA.summary.overall_enps;
if (e === null) { enpsEl.textContent = '—'; }
else { enpsEl.textContent = e; enpsEl.className = 'value ' + (e < 0 ? 'score-bad' : (e < 30 ? 'score-med' : 'score-good')); }

if (DATA.insights.length > 0) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li><i class="zv-dot"></i><span>${i}</span></li>`).join('');
}

const scoreCls = s => s < 6 ? 'score-bad' : (s < 8 ? 'score-med' : 'score-good');
document.getElementById('area-tbody').innerHTML = DATA.by_area.map(r => `<tr><td><strong>${esc(r.segment)}</strong></td><td class="num">${r.n}</td><td class="num ${scoreCls(r.avg_score)}">${r.avg_score}</td><td class="num">${r.min_score}</td><td class="num">${r.max_score}</td></tr>`).join('');
document.getElementById('tenure-tbody').innerHTML = DATA.by_tenure.map(r => `<tr><td><strong>${esc(r.segment)}</strong></td><td class="num">${r.n}</td><td class="num ${scoreCls(r.avg_score)}">${r.avg_score}</td><td class="num">${r.min_score}</td><td class="num">${r.max_score}</td></tr>`).join('');
document.getElementById('lvl-tbody').innerHTML = DATA.by_level.map(r => `<tr><td><strong>${esc(r.segment)}</strong></td><td class="num">${r.n}</td><td class="num ${scoreCls(r.avg_score)}">${r.avg_score}</td><td class="num">${r.min_score}</td><td class="num">${r.max_score}</td></tr>`).join('');
document.getElementById('mgr-tbody').innerHTML = DATA.bottom_managers.map(r => `<tr><td>${esc(r.manager)}</td><td class="num">${r.n}</td><td class="num ${scoreCls(r.avg_score)}">${r.avg_score}</td></tr>`).join('');
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Engagement deep dive: segmenta survey por área/tenure/manager/level.")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path)
    for k in ALIASES:
        p.add_argument(f"--{k.replace('_','-')}-col")
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    headers, rows = load_csv(args.input)
    cols = {k: getattr(args, f"{k}_col", None) or auto_detect(headers, k) for k in ALIASES}
    if not cols.get("score") and not cols.get("enps"):
        sys.exit("Pelo menos uma coluna de score ou eNPS é necessária.")

    print(f"Rows: {len(rows)} | Detected: {[k for k,v in cols.items() if v]}")
    data = analyze(rows, cols)
    out = args.output or Path.cwd() / f"engagement-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    print(f"  Score: {data['summary']['overall_score']} | eNPS: {data['summary']['overall_enps']}")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=engagement-deep-dive")
    return 0


if __name__ == "__main__":
    sys.exit(main())
