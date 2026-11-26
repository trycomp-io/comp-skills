#!/usr/bin/env python3
"""
comp_ratio.py — Analisa compa-ratio (salário atual ÷ mediana da banda) de
um roster contra faixas salariais. Identifica clusters under-paid / fair /
over-paid, heatmap por área × nível, custo pra equalizar, top outliers.

Inputs:
  - Roster CSV: name, salary, level, area (mínimo)
  - Salary table CSV: level, mid (mediana), min (opcional), max (opcional)

Output: HTML executivo com distribuição compa-ratio + ações sugeridas.

Uso:
    python3 comp_ratio.py --roster roster.csv --bands bands.csv
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
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "comp-ratio-analyzer"
SKILL_VERSION = "1.0.0"


# ---------- Zivo visual (zivo-html-guidelines) ----------
ZIVO_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Marcellus&family=Source+Sans+3:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">'
)

ZIVO_CSS = """
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
.zv-dot { display: inline-block; width: 8px; height: 8px; background: currentColor; margin-right: 8px; vertical-align: 1px; }
.zv-dot--red { background: var(--zivo-red); }
.zv-header-row {
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--gap);
  padding-bottom: 10px; margin-bottom: 40px;
  border-bottom: 1px solid var(--zivo-ink-30);
  font-size: 12px; line-height: 16px; text-transform: uppercase; letter-spacing: .04em;
}
.hero { background: var(--zivo-ink); color: var(--zivo-white); padding: 32px 0 48px; }
.hero-inner { max-width: 1120px; margin: 0 auto; padding: 0 32px; }
.hero .zv-header-row { border-bottom-color: rgba(255,255,255,.3); color: rgba(255,255,255,.8); }
.hero h1 { color: var(--zivo-white); max-width: 22ch; }
.hero-sub { margin: 16px 0 0; color: rgba(255,255,255,.7); font-family: var(--zivo-font-flare); font-size: 22px; line-height: 28px; max-width: 60ch; }
.hero-main { display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; }
.logo-tile { width: 56px; height: 56px; display: grid; place-items: center; background: var(--zivo-white); color: var(--zivo-ink); font-family: var(--zivo-font-flare); font-size: 28px; }
.logo-tile img { max-width: 44px; max-height: 44px; }
.page { max-width: 1120px; margin: 0 auto; padding: 48px 32px; }
.section { margin-bottom: 48px; }
.section > h2 { margin-bottom: 16px; }
.card { background: var(--zivo-white); border: 1px solid var(--zivo-ink-10); padding: 24px; }
.card + .card { margin-top: var(--gap); }
.card h3 { margin-bottom: 12px; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
.stat-card { background: var(--zivo-white); border: 1px solid var(--zivo-ink-10); padding: 20px; }
.stat-card .value { font-family: var(--zivo-font-flare); font-size: 40px; line-height: 44px; margin-top: 8px; font-variant-numeric: tabular-nums; }
.stat-card .value.accent { color: var(--zivo-red); }
.stat-card .context { font-size: 14px; line-height: 20px; color: var(--zivo-ink-80); margin-top: 8px; }
.trend-up { color: var(--zivo-success); }
.trend-down { color: var(--zivo-error); }
.trend-flat { color: var(--zivo-ink-60); }
.big-number .value { font-family: var(--zivo-font-flare); font-size: 96px; line-height: 92px; letter-spacing: -0.02em; }
.big-number .rule { height: 1px; background: var(--zivo-ink); margin: 16px 0; }
.big-number .label { font-size: 22px; line-height: 28px; text-transform: none; letter-spacing: 0; color: var(--zivo-ink); }
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
.badge { display: inline-block; white-space: nowrap; padding: 2px 10px; border-radius: 999px; font-size: 12px; line-height: 18px; font-weight: 700; background: var(--zivo-ink-05); color: var(--zivo-ink); }
.badge-good { background: var(--zivo-success-bg); color: var(--zivo-success); }
.badge-warn { background: var(--zivo-warning-bg); color: var(--zivo-warning); }
.badge-bad  { background: var(--zivo-error-bg);   color: var(--zivo-error); }
.badge-info { background: var(--zivo-info-bg);    color: var(--zivo-info); }
.meter { height: 8px; background: var(--zivo-ink-10); }
.meter > span { display: block; height: 100%; background: var(--zivo-ink); }
.callout { background: var(--zivo-white); border-top: 1px solid var(--zivo-ink); padding: 16px 0 0; }
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
"""

ZIVO_WORDMARK = (
    '<svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg>'
)


def _zivo_footer(slug: str) -> str:
    return (
        '<footer class="site-footer">'
        '<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer'
        f'&amp;utm_campaign=eam&amp;utm_content={slug}" aria-label="Zivo">{ZIVO_WORDMARK}</a>'
        '<span>Powered by Zivo · free skills for HR &amp; People leaders</span>'
        '</footer>'
    )


def _zivo_hero(captions, title: str, sub: str = "", aside: str = "") -> str:
    """Ink hero band. All arguments must already be HTML-escaped."""
    caps = "".join(
        (f'<span><i class="zv-dot zv-dot--red"></i>{c}</span>' if i == 0 else f"<span>{c}</span>")
        for i, c in enumerate(["Zivo"] + [c for c in captions if c][:3])
    )
    sub_html = f'<p class="hero-sub">{sub}</p>' if sub else ""
    body = f"<div><h1>{title}</h1>{sub_html}</div>"
    if aside:
        body = f'<div class="hero-main">{body}{aside}</div>'
    return (
        '<header class="hero"><div class="hero-inner">'
        f'<div class="zv-header-row">{caps}</div>{body}'
        "</div></header>"
    )
# ---------------------------------------------------------


ROSTER_ALIASES = {
    "name":   ["name", "nome", "colaborador"],
    "salary": ["salary", "salario", "salário", "salario_base"],
    "level":  ["level", "nivel", "nível", "senioridade"],
    "area":   ["area", "área", "departamento", "department"],
}
BAND_ALIASES = {
    "level": ["level", "nivel", "nível", "grade"],
    "mid":   ["mid", "mediana", "median", "p50", "midpoint"],
    "min":   ["min", "minimo", "mínimo", "p25"],
    "max":   ["max", "maximo", "máximo", "p75"],
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
    s = str(v).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def classify_compa(ratio):
    if ratio is None: return "unknown"
    if ratio < 0.80: return "under"
    if ratio < 0.95: return "below"
    if ratio <= 1.05: return "at"
    if ratio <= 1.20: return "above"
    return "over"


def analyze(roster, bands_lookup, cols_r):
    classified = []
    for row in roster:
        name = row.get(cols_r.get("name") or "", "")
        salary = _f(row.get(cols_r["salary"]))
        level = (row.get(cols_r.get("level") or "") or "").strip()
        area = (row.get(cols_r.get("area") or "") or "—").strip()
        if not salary or not level or level not in bands_lookup:
            continue
        mid = bands_lookup[level]["mid"]
        if not mid or mid <= 0:
            continue
        ratio = round(salary / mid, 3)
        classified.append({
            "name": name, "salary": salary, "level": level, "area": area,
            "mid": mid, "ratio": ratio, "class": classify_compa(ratio),
            "delta_to_mid": round(salary - mid, 2),
        })

    distribution = defaultdict(int)
    by_area_level = defaultdict(lambda: {"total": 0, "ratios": []})
    by_level = defaultdict(lambda: {"total": 0, "ratios": []})
    cost_to_mid = 0  # mensal: levar todos under pra mediana
    for c in classified:
        distribution[c["class"]] += 1
        by_area_level[(c["area"], c["level"])]["total"] += 1
        by_area_level[(c["area"], c["level"])]["ratios"].append(c["ratio"])
        by_level[c["level"]]["total"] += 1
        by_level[c["level"]]["ratios"].append(c["ratio"])
        if c["ratio"] < 1.0:
            cost_to_mid += (c["mid"] - c["salary"])

    by_level_rows = sorted([
        {"level": lvl, "total": v["total"],
         "avg_ratio": round(sum(v["ratios"]) / len(v["ratios"]), 3),
         "min_ratio": round(min(v["ratios"]), 3),
         "max_ratio": round(max(v["ratios"]), 3)}
        for lvl, v in by_level.items()
    ], key=lambda x: x["level"])

    under_outliers = sorted([c for c in classified if c["class"] == "under"],
                            key=lambda c: c["ratio"])[:10]
    over_outliers = sorted([c for c in classified if c["class"] == "over"],
                           key=lambda c: -c["ratio"])[:10]

    insights = []
    total = len(classified)
    if total == 0:
        insights.append("Nenhum colaborador pôde ser analisado — verifique se levels do roster batem com a tabela de bandas.")
    else:
        under_count = distribution["under"] + distribution["below"]
        over_count = distribution["above"] + distribution["over"]
        pct_under = round(under_count / total * 100, 1)
        pct_over = round(over_count / total * 100, 1)
        insights.append(f"<strong>{pct_under}%</strong> dos colaboradores ({under_count}/{total}) abaixo de 95% da mediana — risco de turnover por comp.")
        insights.append(f"<strong>{pct_over}%</strong> ({over_count}/{total}) acima de 105% — pode indicar legacy/exceções/justa retenção.")
        insights.append(f"Custo mensal pra equalizar todos abaixo da mediana: <strong>R$ {cost_to_mid:,.2f}</strong> (anual c/ encargos ≈ R$ {cost_to_mid * 12 * 1.555:,.2f}).".replace(",", "X").replace(".", ",").replace("X", "."))
        if distribution["under"] >= 3:
            insights.append(f"<strong>{distribution['under']} colaborador(es)</strong> abaixo de 80% (banda 1) — prioridade urgente de revisão.")

    return {
        "summary": {
            "total_analyzed": total,
            "total_roster": len(roster),
            "cost_monthly_to_mid": round(cost_to_mid, 2),
            "cost_annual_loaded": round(cost_to_mid * 12 * 1.555, 2),
        },
        "distribution": {k: distribution[k] for k in ("under", "below", "at", "above", "over")},
        "by_level": by_level_rows,
        "under_outliers": under_outliers,
        "over_outliers": over_outliers,
        "insights": insights,
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Comp ratio analysis · Zivo</title>
__ZIVO_FONTS__
<style>__ZIVO_CSS__</style>
<style>
  .dist{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:16px}
  .dist .stat-card .value{margin:8px 0 4px}
  .insights{list-style:none;padding:0;margin:0}
  .insights li{padding:10px 0;border-top:1px solid var(--zivo-ink-10)}
  .insights li:first-child{border-top:none;padding-top:0}
  .stat-grid .stat-card .value{font-size:32px;line-height:38px;white-space:nowrap}
  .two-col{display:grid;grid-template-columns:1fr;gap:24px}
  .two-col .card{margin:0}
  .two-col td:first-child{white-space:nowrap}
  .two-col h3{margin-bottom:12px}
  td.num,th.num{white-space:nowrap}
  .gap-neg{color:var(--zivo-error)}
  .gap-pos{color:var(--zivo-success)}
</style></head>
<body>
<header class="hero"><div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>Comp ratio</span><span id="generated"></span><span>Confidencial</span></div>
<h1 id="hero-title">Distribuição salarial vs bandas</h1>
<p class="hero-sub">Compa-ratio (salário ÷ mediana da banda) do roster, por nível e faixa.</p>
</div></header>

<main class="page">

<section class="section">
<div class="stat-grid">
<div class="stat-card"><div class="label">Analisados</div><div class="value" id="s-analyzed"></div><div class="context">Com nível presente na tabela de bandas.</div></div>
<div class="stat-card"><div class="label">Roster total</div><div class="value" id="s-total"></div><div class="context">Linhas no CSV de roster.</div></div>
<div class="stat-card"><div class="label">Custo equalizar (mensal)</div><div class="value accent" id="s-cost"></div><div class="context">Levar todos abaixo da mediana até ela.</div></div>
<div class="stat-card"><div class="label">Anual c/ encargos</div><div class="value" id="s-cost-y"></div><div class="context">12 meses × 1,555 de encargos.</div></div>
</div>
</section>

<section class="section">
<h2>Distribuição</h2>
<div class="dist" id="dist"></div>
</section>

<section class="section" id="insights-card" style="display:none;">
<h2>Insights</h2>
<div class="card"><ul class="insights" id="insights-list"></ul></div>
</section>

<section class="section">
<h2>Por nível</h2>
<div class="card table-wrap"><table><thead><tr><th>Nível</th><th class="num">HC</th><th class="num">Compa ratio médio</th><th class="num">Min</th><th class="num">Max</th></tr></thead><tbody id="lvl-tbody"></tbody></table></div>
</section>

<section class="section">
<h2>Outliers</h2>
<div class="two-col">
<div class="card table-wrap"><h3>Top 10 under-paid</h3><table><thead><tr><th>Nome</th><th>Nível</th><th class="num">Salário</th><th class="num">Mediana</th><th>Ratio</th><th class="num">Gap</th></tr></thead><tbody id="under-tbody"></tbody></table></div>
<div class="card table-wrap"><h3>Top 10 over-paid</h3><table><thead><tr><th>Nome</th><th>Nível</th><th class="num">Salário</th><th class="num">Mediana</th><th>Ratio</th><th class="num">Gap</th></tr></thead><tbody id="over-tbody"></tbody></table></div>
</div>
</section>

</main>
__ZIVO_FOOTER__

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'short', year:'numeric' });
const fmt = v => 'R$ ' + v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

document.getElementById('s-analyzed').textContent = DATA.summary.total_analyzed;
document.getElementById('s-total').textContent = DATA.summary.total_roster;
document.getElementById('s-cost').textContent = fmt(DATA.summary.cost_monthly_to_mid);
document.getElementById('s-cost-y').textContent = fmt(DATA.summary.cost_annual_loaded);

if (DATA.summary.total_analyzed > 0) {
  const below = (DATA.distribution.under || 0) + (DATA.distribution.below || 0);
  const pct = (below / DATA.summary.total_analyzed * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 });
  document.getElementById('hero-title').textContent = pct + '% do time ganha abaixo de 95% da mediana da banda';
}

const distLabels = { under: '<80% Under', below: '80-95% Below', at: '95-105% At target', above: '105-120% Above', over: '>120% Over' };
const distClass = { under: 'badge-bad', below: 'badge-warn', at: 'badge-good', above: 'badge-info', over: 'badge-warn' };
document.getElementById('dist').innerHTML = ['under','below','at','above','over'].map(k =>
  `<div class="stat-card">
    <span class="badge ${distClass[k]}">${esc(distLabels[k])}</span>
    <div class="value">${DATA.distribution[k] || 0}</div>
    <div class="context">colaborador(es)</div>
  </div>`).join('');

if (DATA.insights.length > 0) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li><i class="zv-dot"></i>${i}</li>`).join('');
}

document.getElementById('lvl-tbody').innerHTML = DATA.by_level.map(l =>
  `<tr><td><strong>${esc(l.level)}</strong></td><td class="num">${l.total}</td><td class="num">${l.avg_ratio}</td><td class="num">${l.min_ratio}</td><td class="num">${l.max_ratio}</td></tr>`).join('');

document.getElementById('under-tbody').innerHTML = DATA.under_outliers.map(c =>
  `<tr><td>${esc(c.name)}</td><td>${esc(c.level)}</td><td class="num">${fmt(c.salary)}</td><td class="num">${fmt(c.mid)}</td><td><span class="badge ${distClass[c.class]}">${c.ratio}</span></td><td class="num gap-neg">${fmt(c.delta_to_mid)}</td></tr>`).join('');
document.getElementById('over-tbody').innerHTML = DATA.over_outliers.map(c =>
  `<tr><td>${esc(c.name)}</td><td>${esc(c.level)}</td><td class="num">${fmt(c.salary)}</td><td class="num">${fmt(c.mid)}</td><td><span class="badge ${distClass[c.class]}">${c.ratio}</span></td><td class="num gap-pos">+${fmt(c.delta_to_mid)}</td></tr>`).join('');
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    html = (TEMPLATE.replace("__ZIVO_FONTS__", ZIVO_FONTS)
            .replace("__ZIVO_CSS__", ZIVO_CSS)
            .replace("__ZIVO_FOOTER__", _zivo_footer(SKILL_NAME))
            .replace("__DATA__", payload))
    out.write_text(html, encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Análise de compa-ratio do roster contra bandas salariais.")
    p.add_argument("--roster", type=Path, required=True)
    p.add_argument("--bands", type=Path, required=True, help="CSV com colunas level, mid (mediana)")
    p.add_argument("--output", type=Path)
    p.add_argument("--name-col"); p.add_argument("--salary-col"); p.add_argument("--level-col"); p.add_argument("--area-col")
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    headers_r, roster = load_csv(args.roster)
    cols_r = {k: getattr(args, f"{k}_col", None) or auto_detect(headers_r, ROSTER_ALIASES, k) for k in ROSTER_ALIASES}
    if not cols_r.get("salary") or not cols_r.get("level"):
        sys.exit("Roster precisa de salary + level. Verifique colunas.")

    headers_b, bands = load_csv(args.bands)
    cols_b = {k: auto_detect(headers_b, BAND_ALIASES, k) for k in BAND_ALIASES}
    if not cols_b.get("level") or not cols_b.get("mid"):
        sys.exit("Bands CSV precisa de level + mid (mediana).")

    bands_lookup = {}
    for b in bands:
        lvl = (b.get(cols_b["level"]) or "").strip()
        mid = _f(b.get(cols_b["mid"]))
        if lvl and mid:
            bands_lookup[lvl] = {"mid": mid}

    print(f"Roster: {len(roster)} | Bands: {len(bands_lookup)} levels")
    data = analyze(roster, bands_lookup, cols_r)
    out = args.output or Path.cwd() / f"comp-ratio-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    print(f"  {data['summary']['total_analyzed']} analisados | custo mensal pra equalizar: R$ {data['summary']['cost_monthly_to_mid']:,.2f}".replace(",", "."))

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=comp-ratio-analyzer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
