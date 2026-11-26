#!/usr/bin/env python3
"""
promotion_equity.py — Analisa equidade de promoções por demografia.

Input CSV mínimo: gender (ou outra dimensão). Recomendado: promoted (1/0),
date, area, level_before, level_after, tenure_at_promotion.

Output: HTML executivo com taxa de promoção por demografia, gap vs eligible
population, áreas/níveis com maior disparidade. Defensável pra compliance.

Uso:
    python3 promotion_equity.py --input promotions.csv \\
        --eligible-population roster.csv

Quando --eligible-population é fornecido, calcula taxa real (promoções ÷
população elegível) por gênero — caso contrário só mostra a distribuição
das promoções acontecidas.
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

SKILL_NAME = "promotion-equity-analyzer"
SKILL_VERSION = "1.0.0"


ALIASES = {
    "gender":             ["gender", "genero", "gênero", "sexo", "sex"],
    "promoted":           ["promoted", "promovido", "promoted_yn"],
    "date":               ["date", "data", "promotion_date", "data_promocao"],
    "area":               ["area", "área", "departamento", "department"],
    "level_before":       ["level_before", "nivel_anterior", "before", "from_level"],
    "level_after":        ["level_after", "nivel_novo", "after", "to_level"],
    "tenure_months":      ["tenure_months", "tenure", "tempo_casa", "tempo_meses"],
    "race":               ["race", "raca", "raça", "ethnicity"],
}

FEMALE = {"f", "female", "feminino", "fem", "mulher"}
MALE = {"m", "male", "masculino", "masc", "homem"}


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


def norm_gender(v):
    if not v: return None
    s = _norm(v)
    if s in FEMALE: return "F"
    if s in MALE: return "M"
    return None


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def analyze(promotions, eligible, cols_p, cols_e):
    # 1) Counts de promoções por gênero
    promo_by_gender = defaultdict(int)
    promo_by_area_gender = defaultdict(lambda: defaultdict(int))
    promo_by_levels = defaultdict(int)
    for row in promotions:
        g = norm_gender(row.get(cols_p["gender"]))
        if not g:
            continue
        promo_by_gender[g] += 1
        area = (row.get(cols_p.get("area") or "") or "—").strip()
        promo_by_area_gender[area][g] += 1
        before = (row.get(cols_p.get("level_before") or "") or "").strip()
        after = (row.get(cols_p.get("level_after") or "") or "").strip()
        if before and after:
            promo_by_levels[f"{before} → {after}"] += 1

    # 2) Eligible population (se fornecido)
    eligible_by_gender = defaultdict(int)
    eligible_by_area_gender = defaultdict(lambda: defaultdict(int))
    if eligible and cols_e and cols_e.get("gender"):
        for row in eligible:
            g = norm_gender(row.get(cols_e["gender"]))
            if not g:
                continue
            eligible_by_gender[g] += 1
            area = (row.get(cols_e.get("area") or "") or "—").strip()
            eligible_by_area_gender[area][g] += 1

    # 3) Taxa de promoção por gênero (se eligible disponível)
    rates = {}
    if eligible_by_gender:
        for g in ("F", "M"):
            elig = eligible_by_gender.get(g, 0)
            promo = promo_by_gender.get(g, 0)
            rates[g] = {
                "promoted": promo, "eligible": elig,
                "rate_pct": round(promo / elig * 100, 2) if elig else 0,
            }
        # Gap
        gap = None
        if rates.get("F") and rates.get("M") and rates["M"]["rate_pct"]:
            gap = round((rates["F"]["rate_pct"] / rates["M"]["rate_pct"] - 1) * 100, 1)
    else:
        gap = None

    # 4) Top areas com disparidade (precisa eligible)
    disparities = []
    if eligible_by_area_gender:
        for area in eligible_by_area_gender:
            f_elig = eligible_by_area_gender[area].get("F", 0)
            m_elig = eligible_by_area_gender[area].get("M", 0)
            f_prom = promo_by_area_gender[area].get("F", 0)
            m_prom = promo_by_area_gender[area].get("M", 0)
            if f_elig < 3 or m_elig < 3:
                continue
            f_rate = f_prom / f_elig * 100
            m_rate = m_prom / m_elig * 100
            if m_rate == 0:
                continue
            ratio = f_rate / m_rate
            disparities.append({
                "area": area, "f_eligible": f_elig, "m_eligible": m_elig,
                "f_promoted": f_prom, "m_promoted": m_prom,
                "f_rate": round(f_rate, 2), "m_rate": round(m_rate, 2),
                "ratio_f_to_m": round(ratio, 2),
            })
        disparities.sort(key=lambda x: abs(x["ratio_f_to_m"] - 1), reverse=True)

    # 5) Insights
    insights = []
    if not rates:
        insights.append("Sem população elegível fornecida — análise mostra apenas distribuição das promoções. Pra taxas reais, forneça --eligible-population.")
    else:
        f_rate = rates.get("F", {}).get("rate_pct", 0)
        m_rate = rates.get("M", {}).get("rate_pct", 0)
        if gap is not None:
            if gap < -15:
                insights.append(f"<strong>Mulheres com taxa de promoção {abs(gap)}% MENOR</strong> que homens ({f_rate}% vs {m_rate}%). Diferença significativa — investigar critérios de promoção e bench identificado.")
            elif gap > 15:
                insights.append(f"Mulheres com taxa de promoção {gap}% MAIOR que homens ({f_rate}% vs {m_rate}%). Não-óbvio — entender se é correção histórica ou anomalia da janela.")
            else:
                insights.append(f"Taxa de promoção próxima por gênero (gap {gap}%, F {f_rate}% vs M {m_rate}%). Boa equidade nesta janela.")
    if disparities:
        worst = disparities[0]
        if abs(worst["ratio_f_to_m"] - 1) > 0.3:
            insights.append(f"Área <strong>{_esc(worst['area'])}</strong> com maior disparidade: ratio F/M = {worst['ratio_f_to_m']} (F {worst['f_rate']}% vs M {worst['m_rate']}%).")
    if promo_by_gender.get("F", 0) + promo_by_gender.get("M", 0) < 20:
        insights.append("Amostra pequena (<20 promoções). Tome conclusões com cautela e amplie a janela temporal se possível.")

    return {
        "summary": {
            "total_promotions": sum(promo_by_gender.values()),
            "by_gender": dict(promo_by_gender),
            "has_eligible": bool(eligible_by_gender),
            "gap_f_vs_m_pct": gap,
        },
        "rates": rates,
        "by_levels": [{"transition": k, "count": v} for k, v in sorted(promo_by_levels.items(), key=lambda x: -x[1])[:15]],
        "by_area": [{"area": a, **{g: d.get(g, 0) for g in ("F", "M")}} for a, d in promo_by_area_gender.items()],
        "disparities": disparities[:10],
        "insights": insights,
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Promotion Equity Analysis · Zivo</title>
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
  .gap-neg{color:#B3172A}.gap-pos{color:#0B7A43}.gap-neutral{color:rgba(26,26,26,.6)}
</style></head>
<body>
<header class="hero"><div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>Promotion equity</span><span><span id="generated"></span></span><span>Confidencial</span></div>
<h1>Equidade de promoções por gênero</h1>
<p class="hero-sub">Taxa de promoção por gênero, disparidade por área e transições de nível.</p>
</div></header>
<main class="page">

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
<div class="card"><div class="stat-label">Total promoções</div><div class="stat" id="s-total"></div></div>
<div class="card"><div class="stat-label">Promoções F</div><div class="stat" id="s-f"></div></div>
<div class="card"><div class="stat-label">Promoções M</div><div class="stat" id="s-m"></div></div>
<div class="card"><div class="stat-label">Gap F vs M</div><div class="stat" id="s-gap"></div></div>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2>Insights</h2>
<ul class="space-y-2 zv-list" id="insights-list"></ul>
</div>

<div class="card" id="rates-card" style="display:none;">
<h2>Taxa de promoção por gênero</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Gênero</th><th>Elegíveis</th><th>Promovidos</th><th>Taxa</th></tr></thead><tbody id="rates-tbody"></tbody></table></div>
</div>

<div class="card" id="disp-card" style="display:none;">
<h2>Áreas com maior disparidade</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Área</th><th>F elig</th><th>F prom</th><th>F taxa</th><th>M elig</th><th>M prom</th><th>M taxa</th><th>Ratio F/M</th></tr></thead><tbody id="disp-tbody"></tbody></table></div>
</div>

<div class="card">
<h2>Transições de nível</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Transição</th><th>Ocorrências</th></tr></thead><tbody id="lvl-tbody"></tbody></table></div>
</div>

</main>
<footer class="site-footer">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=promotion-equity-analyzer" aria-label="Zivo"><svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg></a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });

document.getElementById('s-total').textContent = DATA.summary.total_promotions;
document.getElementById('s-f').textContent = DATA.summary.by_gender.F || 0;
document.getElementById('s-m').textContent = DATA.summary.by_gender.M || 0;
const gap = DATA.summary.gap_f_vs_m_pct;
const gapEl = document.getElementById('s-gap');
if (gap === null) { gapEl.textContent = '—'; gapEl.className = 'stat gap-neutral'; }
else { gapEl.textContent = (gap > 0 ? '+' : '') + gap + '%'; gapEl.className = 'stat ' + (gap < -10 ? 'gap-neg' : (gap > 10 ? 'gap-pos' : 'gap-neutral')); }

if (DATA.insights.length > 0) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li class="flex items-start"><i class="zv-dot"></i><span>${i}</span></li>`).join('');
}

if (DATA.summary.has_eligible) {
  document.getElementById('rates-card').style.display = '';
  document.getElementById('rates-tbody').innerHTML = Object.entries(DATA.rates).map(([g, r]) =>
    `<tr><td><strong>${esc(g)}</strong></td><td>${r.eligible}</td><td>${r.promoted}</td><td>${r.rate_pct}%</td></tr>`).join('');
  if (DATA.disparities.length > 0) {
    document.getElementById('disp-card').style.display = '';
    document.getElementById('disp-tbody').innerHTML = DATA.disparities.map(d =>
      `<tr><td><strong>${esc(d.area)}</strong></td><td>${d.f_eligible}</td><td>${d.f_promoted}</td><td>${d.f_rate}%</td><td>${d.m_eligible}</td><td>${d.m_promoted}</td><td>${d.m_rate}%</td><td><strong>${d.ratio_f_to_m}</strong></td></tr>`).join('');
  }
}

document.getElementById('lvl-tbody').innerHTML = DATA.by_levels.map(l =>
  `<tr><td>${esc(l.transition)}</td><td><strong>${l.count}</strong></td></tr>`).join('');
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Analisa equidade de promoções por gênero.")
    p.add_argument("--input", type=Path, required=True, help="CSV de promoções")
    p.add_argument("--eligible-population", type=Path, help="CSV opcional com população elegível pra taxa real")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    headers, promotions = load_csv(args.input)
    cols_p = {k: auto_detect(headers, k) for k in ALIASES}
    if not cols_p.get("gender"):
        sys.exit("Coluna 'gender' obrigatória.")

    eligible = []
    cols_e = {}
    if args.eligible_population:
        h_e, eligible = load_csv(args.eligible_population)
        cols_e = {k: auto_detect(h_e, k) for k in ALIASES}

    print(f"Promotions: {len(promotions)} | Eligible: {len(eligible)}")
    data = analyze(promotions, eligible, cols_p, cols_e)
    out = args.output or Path.cwd() / f"promotion-equity-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    print(f"  Total: {data['summary']['total_promotions']} | F: {data['summary']['by_gender'].get('F', 0)} | M: {data['summary']['by_gender'].get('M', 0)}")
    if data['summary']['gap_f_vs_m_pct'] is not None:
        print(f"  Gap F vs M: {data['summary']['gap_f_vs_m_pct']}%")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=promotion-equity-analyzer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
