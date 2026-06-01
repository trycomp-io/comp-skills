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
<meta charset="UTF-8"><title>Promotion Equity Analysis — Comp</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  body{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b}
  .card{background:white;border-radius:12px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin-bottom:1.5rem}
  .stat{font-size:2.25rem;font-weight:800}
  .stat-label{font-size:.875rem;color:#64748b;text-transform:uppercase;font-weight:600}
  table{width:100%;border-collapse:collapse;font-size:.85rem}
  th{background:#1e293b;color:white;padding:.65rem;text-align:left;font-size:.75rem;text-transform:uppercase}
  td{padding:.65rem;border-bottom:1px solid #e2e8f0}
  .gap-neg{color:#dc2626;font-weight:700}.gap-pos{color:#10b981;font-weight:700}.gap-neutral{color:#64748b}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-6xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Promotion Equity</div>
<h1 class="text-3xl font-extrabold text-slate-900">Equidade de promoções por gênero</h1>
<p class="text-sm text-slate-500 mt-2" id="generated"></p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
<div class="card"><div class="stat-label">Total promoções</div><div class="stat" id="s-total"></div></div>
<div class="card"><div class="stat-label">Promoções F</div><div class="stat" id="s-f"></div></div>
<div class="card"><div class="stat-label">Promoções M</div><div class="stat" id="s-m"></div></div>
<div class="card"><div class="stat-label">Gap F vs M</div><div class="stat" id="s-gap"></div></div>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Insights</h2>
<ul class="space-y-2" id="insights-list"></ul>
</div>

<div class="card" id="rates-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Taxa de promoção por gênero</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Gênero</th><th>Elegíveis</th><th>Promovidos</th><th>Taxa</th></tr></thead><tbody id="rates-tbody"></tbody></table></div>
</div>

<div class="card" id="disp-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Áreas com maior disparidade</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Área</th><th>F elig</th><th>F prom</th><th>F taxa</th><th>M elig</th><th>M prom</th><th>M taxa</th><th>Ratio F/M</th></tr></thead><tbody id="disp-tbody"></tbody></table></div>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Transições de nível</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Transição</th><th>Ocorrências</th></tr></thead><tbody id="lvl-tbody"></tbody></table></div>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=promotion-equity-analyzer" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div>

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
    `<li class="flex items-start"><span class="text-rose-500 font-bold mr-2">●</span><span>${i}</span></li>`).join('');
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
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=promotion-equity-analyzer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
