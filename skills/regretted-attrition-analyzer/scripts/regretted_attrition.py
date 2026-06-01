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
<meta charset="UTF-8"><title>Regretted Attrition Analysis — Comp</title>
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
  .pct-high{color:#dc2626;font-weight:700}.pct-med{color:#f59e0b;font-weight:600}.pct-low{color:#10b981}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-6xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Regretted Attrition</div>
<h1 class="text-3xl font-extrabold text-slate-900">Análise de turnover lamentado</h1>
<p class="text-sm text-slate-500 mt-2" id="generated"></p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
<div class="card"><div class="stat-label">Total desligamentos</div><div class="stat text-slate-900" id="s-total"></div></div>
<div class="card"><div class="stat-label">Regretted</div><div class="stat text-rose-600" id="s-reg"></div></div>
<div class="card"><div class="stat-label">Unregretted</div><div class="stat text-emerald-600" id="s-unreg"></div></div>
<div class="card"><div class="stat-label">% Regretted</div><div class="stat text-slate-900" id="s-pct"></div></div>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Insights pra ação</h2>
<ul class="space-y-2" id="insights-list"></ul>
</div>

<div class="grid sm:grid-cols-2 gap-6">
<div class="card"><h2 class="text-xl font-bold mb-4">Por área</h2><div class="overflow-x-auto"><table><thead><tr><th>Área</th><th>Total</th><th>Regretted</th><th>%</th></tr></thead><tbody id="area-tbody"></tbody></table></div></div>
<div class="card"><h2 class="text-xl font-bold mb-4">Por tenure</h2><div class="overflow-x-auto"><table><thead><tr><th>Faixa</th><th>Total</th><th>Regretted</th><th>%</th></tr></thead><tbody id="tenure-tbody"></tbody></table></div></div>
<div class="card"><h2 class="text-xl font-bold mb-4">Por performance</h2><div class="overflow-x-auto"><table><thead><tr><th>Banda</th><th>Total</th><th>Regretted</th><th>%</th></tr></thead><tbody id="perf-tbody"></tbody></table></div></div>
<div class="card"><h2 class="text-xl font-bold mb-4">Top 10 gestores com regretted</h2><div class="overflow-x-auto"><table><thead><tr><th>Gestor</th><th>Total</th><th>Regretted</th><th>%</th></tr></thead><tbody id="mgr-tbody"></tbody></table></div></div>
</div>

<div class="card" id="reasons-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Top motivos declarados</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Motivo</th><th>Ocorrências</th></tr></thead><tbody id="reasons-tbody"></tbody></table></div>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=regretted-attrition-analyzer" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div>

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
    `<li class="flex items-start"><span class="text-rose-500 font-bold mr-2">●</span><span>${i}</span></li>`).join('');
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
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=regretted-attrition-analyzer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
