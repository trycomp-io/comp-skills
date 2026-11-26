#!/usr/bin/env python3
"""
regretted_attrition.py — Analisa CSV de desligamentos e identifica padrões
em regretted vs unregretted: top correlated factors (manager, área, tenure
band, performance band), heatmap por área e tempo, insights.

Input CSV mínimo: regretted (1/0). Recomendado: area, level, tenure_months,
performance_rating, manager_id, departure_reason.

Output: HTML executivo + insights pra CHRO levar pro CEO.

Uso:
    python3 regretted_attrition.py --input departures.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "regretted-attrition-analyzer"
SKILL_VERSION = "1.0.0"


ALIASES = {
    "name":               ["name", "nome", "colaborador"],
    "regretted":          ["regretted", "lamentado", "regretted_yn", "indesejado", "voluntary_loss"],
    "area":               ["area", "área", "departamento", "department"],
    "level":              ["level", "nivel", "nível", "senioridade"],
    "tenure_months":      ["tenure_months", "tenure", "tempo_casa", "tempo_meses"],
    "performance_rating": ["performance", "performance_rating", "rating", "nota"],
    "manager_id":         ["manager_id", "manager", "gestor", "gestor_id"],
    "departure_reason":   ["reason", "departure_reason", "motivo", "motivo_saida"],
    "departure_date":     ["departure_date", "data_saida", "data_desligamento", "exit_date"],
}


def _esc(v):
    import html
    return html.escape(str(v), quote=True) if v is not None else ""


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").strip().lower().replace(" ", "_")


def auto_detect(headers, key):
    h = {_norm(x): x for x in headers}
    for cand in ALIASES[key]:
        if _norm(cand) in h:
            return h[_norm(cand)]
    return None


def _bool(v):
    if v is None or v == "":
        return None
    s = str(v).strip().lower()
    return s in ("1", "yes", "y", "sim", "true", "regretted", "lamentado")


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


def perf_band(r):
    if r is None: return "Desconhecido"
    if r >= 4.5: return "Top"
    if r >= 3.5: return "Strong"
    if r >= 2.5: return "Solid"
    if r >= 1.5: return "Needs improvement"
    return "Low"


def analyze(rows, cols):
    total = len(rows)
    regretted = 0
    unregretted = 0
    unknown = 0
    by_area = defaultdict(lambda: {"total": 0, "regretted": 0})
    by_manager = defaultdict(lambda: {"total": 0, "regretted": 0})
    by_tenure = defaultdict(lambda: {"total": 0, "regretted": 0})
    by_perf = defaultdict(lambda: {"total": 0, "regretted": 0})
    by_level = defaultdict(lambda: {"total": 0, "regretted": 0})
    reasons = Counter()

    for row in rows:
        is_reg = _bool(row.get(cols["regretted"])) if cols.get("regretted") else None
        if is_reg is True: regretted += 1
        elif is_reg is False: unregretted += 1
        else: unknown += 1

        area = (row.get(cols.get("area") or "") or "—") if cols.get("area") else "—"
        manager = (row.get(cols.get("manager_id") or "") or "—") if cols.get("manager_id") else None
        level = (row.get(cols.get("level") or "") or "—") if cols.get("level") else "—"
        tenure = _f(row.get(cols.get("tenure_months") or "")) if cols.get("tenure_months") else None
        perf = _f(row.get(cols.get("performance_rating") or "")) if cols.get("performance_rating") else None
        reason = (row.get(cols.get("departure_reason") or "") or "").strip() if cols.get("departure_reason") else ""

        by_area[area]["total"] += 1
        if is_reg: by_area[area]["regretted"] += 1
        if manager:
            by_manager[manager]["total"] += 1
            if is_reg: by_manager[manager]["regretted"] += 1
        by_level[level]["total"] += 1
        if is_reg: by_level[level]["regretted"] += 1
        tb = tenure_band(tenure)
        by_tenure[tb]["total"] += 1
        if is_reg: by_tenure[tb]["regretted"] += 1
        pb = perf_band(perf)
        by_perf[pb]["total"] += 1
        if is_reg: by_perf[pb]["regretted"] += 1
        if reason: reasons[reason] += 1

    def rank(d, min_total=2):
        return sorted(
            [{"key": k, "total": v["total"], "regretted": v["regretted"],
              "pct": round(v["regretted"] / v["total"] * 100, 1) if v["total"] else 0}
             for k, v in d.items() if v["total"] >= min_total],
            key=lambda x: x["regretted"], reverse=True,
        )

    overall_pct = round(regretted / total * 100, 1) if total else 0

    insights = []
    insights.append(f"<strong>{regretted}/{total} desligamentos ({overall_pct}%) classificados como regretted.</strong>")
    if unknown > 0:
        insights.append(f"{unknown} sem classificação. Considere classificar pra próxima análise — distorce o número final.")

    # Top area
    area_ranked = rank(by_area)
    if area_ranked:
        top_area = area_ranked[0]
        if top_area["pct"] > overall_pct * 1.5 and top_area["regretted"] >= 3:
            insights.append(f"Área <strong>{_esc(top_area['key'])}</strong> tem {top_area['pct']}% regretted ({top_area['regretted']}/{top_area['total']}) — {round(top_area['pct']/overall_pct, 1)}x a média da empresa.")

    # Top manager (com 3+ saídas)
    mgr_ranked = rank(by_manager, min_total=3)
    if mgr_ranked:
        top_mgr = mgr_ranked[0]
        if top_mgr["regretted"] >= 3:
            insights.append(f"Gestor <strong>{_esc(top_mgr['key'])}</strong> concentra {top_mgr['regretted']} desligamentos regretted ({top_mgr['pct']}% do time dele) — pattern pra investigar.")

    # Tenure band
    short_tenure_reg = sum(by_tenure[b]["regretted"] for b in ["0-6m", "6-12m"])
    if short_tenure_reg >= 3 and short_tenure_reg / max(regretted, 1) > 0.3:
        pct = round(short_tenure_reg / regretted * 100, 1)
        insights.append(f"{pct}% dos regretted saem antes de 1 ano — sinal de problema em onboarding, hiring ou alinhamento de expectativas.")

    # Top performers leaving
    top_perf_reg = by_perf.get("Top", {}).get("regretted", 0) + by_perf.get("Strong", {}).get("regretted", 0)
    if top_perf_reg >= 3:
        insights.append(f"<strong>{top_perf_reg} top performers</strong> entre os regretted — investigue saturação, ofertas externas, gap de carreira/comp.")

    return {
        "summary": {
            "total": total, "regretted": regretted, "unregretted": unregretted, "unknown": unknown,
            "pct_regretted": overall_pct,
        },
        "by_area": area_ranked,
        "by_manager_top10": mgr_ranked[:10],
        "by_tenure": [{"key": k, **v} for k, v in by_tenure.items() if v["total"] > 0],
        "by_perf": [{"key": k, **v} for k, v in by_perf.items() if v["total"] > 0],
        "by_level": rank(by_level),
        "top_reasons": [{"reason": r, "count": c} for r, c in reasons.most_common(10)],
        "insights": insights,
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Regretted Attrition Analysis · Zivo</title>
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
  .pct-high{color:#B3172A;font-weight:700}.pct-med{color:#985704;font-weight:700}.pct-low{color:#0B7A43}
</style></head>
<body>
<header class="hero"><div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>Regretted attrition</span><span><span id="generated"></span></span><span>Confidencial</span></div>
<h1>Análise de turnover lamentado</h1>
<p class="hero-sub">Desligamentos regretted vs unregretted por área, tenure, performance e gestor.</p>
</div></header>
<main class="page">

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
<div class="card"><div class="stat-label">Total desligamentos</div><div class="stat" id="s-total"></div></div>
<div class="card"><div class="stat-label">Regretted</div><div class="stat accent" id="s-reg"></div></div>
<div class="card"><div class="stat-label">Unregretted</div><div class="stat" id="s-unreg"></div></div>
<div class="card"><div class="stat-label">% Regretted</div><div class="stat" id="s-pct"></div></div>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2>Insights pra ação</h2>
<ul class="space-y-2 zv-list" id="insights-list"></ul>
</div>

<div class="grid sm:grid-cols-2 gap-6">
<div class="card"><h2>Por área</h2><div class="overflow-x-auto"><table><thead><tr><th>Área</th><th>Total</th><th>Regretted</th><th>%</th></tr></thead><tbody id="area-tbody"></tbody></table></div></div>
<div class="card"><h2>Por tenure</h2><div class="overflow-x-auto"><table><thead><tr><th>Faixa</th><th>Total</th><th>Regretted</th><th>%</th></tr></thead><tbody id="tenure-tbody"></tbody></table></div></div>
<div class="card"><h2>Por performance</h2><div class="overflow-x-auto"><table><thead><tr><th>Banda</th><th>Total</th><th>Regretted</th><th>%</th></tr></thead><tbody id="perf-tbody"></tbody></table></div></div>
<div class="card"><h2>Top 10 gestores com regretted</h2><div class="overflow-x-auto"><table><thead><tr><th>Gestor</th><th>Total</th><th>Regretted</th><th>%</th></tr></thead><tbody id="mgr-tbody"></tbody></table></div></div>
</div>

<div class="card" id="reasons-card" style="display:none;">
<h2>Top motivos declarados</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Motivo</th><th>Ocorrências</th></tr></thead><tbody id="reasons-tbody"></tbody></table></div>
</div>

</main>
<footer class="site-footer">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=regretted-attrition-analyzer" aria-label="Zivo"><svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg></a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });
document.getElementById('s-total').textContent = DATA.summary.total;
document.getElementById('s-reg').textContent = DATA.summary.regretted;
document.getElementById('s-unreg').textContent = DATA.summary.unregretted;
document.getElementById('s-pct').textContent = DATA.summary.pct_regretted + '%';

function pctClass(p) { if (p >= 50) return 'pct-high'; if (p >= 25) return 'pct-med'; return 'pct-low'; }

if (DATA.insights.length > 0) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li class="flex items-start"><i class="zv-dot"></i><span>${i}</span></li>`).join('');
}

document.getElementById('area-tbody').innerHTML = DATA.by_area.map(r =>
  `<tr><td><strong>${esc(r.key)}</strong></td><td>${r.total}</td><td>${r.regretted}</td><td class="${pctClass(r.pct)}">${r.pct}%</td></tr>`).join('');
document.getElementById('tenure-tbody').innerHTML = DATA.by_tenure.map(r => {
  const pct = r.total ? Math.round(r.regretted/r.total*100) : 0;
  return `<tr><td><strong>${esc(r.key)}</strong></td><td>${r.total}</td><td>${r.regretted}</td><td class="${pctClass(pct)}">${pct}%</td></tr>`;
}).join('');
document.getElementById('perf-tbody').innerHTML = DATA.by_perf.map(r => {
  const pct = r.total ? Math.round(r.regretted/r.total*100) : 0;
  return `<tr><td><strong>${esc(r.key)}</strong></td><td>${r.total}</td><td>${r.regretted}</td><td class="${pctClass(pct)}">${pct}%</td></tr>`;
}).join('');
document.getElementById('mgr-tbody').innerHTML = DATA.by_manager_top10.map(r =>
  `<tr><td>${esc(r.key)}</td><td>${r.total}</td><td>${r.regretted}</td><td class="${pctClass(r.pct)}">${r.pct}%</td></tr>`).join('');

if (DATA.top_reasons.length > 0) {
  document.getElementById('reasons-card').style.display = '';
  document.getElementById('reasons-tbody').innerHTML = DATA.top_reasons.map(r =>
    `<tr><td>${esc(r.reason)}</td><td><strong>${r.count}</strong></td></tr>`).join('');
}
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Analisa CSV de desligamentos pra padrões em regretted.")
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

    ext = args.input.suffix.lower()
    if ext != ".csv":
        sys.exit(f"Use CSV. Formato {ext} não suportado.")
    headers, rows = load_csv(args.input)
    cols = {k: getattr(args, f"{k}_col", None) or auto_detect(headers, k) for k in ALIASES}
    if not cols.get("regretted"):
        sys.exit("Coluna 'regretted' obrigatória. Use --regretted-col.")

    print(f"Rows: {len(rows)}. Detected cols: {[k for k,v in cols.items() if v]}")
    data = analyze(rows, cols)
    out = args.output or Path.cwd() / f"regretted-attrition-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    print(f"  {data['summary']['regretted']}/{data['summary']['total']} regretted ({data['summary']['pct_regretted']}%)")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=regretted-attrition-analyzer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
