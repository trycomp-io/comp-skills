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
<meta charset="UTF-8"><title>Engagement Deep Dive — Comp</title>
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
  .score-bad{color:#dc2626;font-weight:700}.score-med{color:#f59e0b}.score-good{color:#10b981;font-weight:600}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-6xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Engagement Deep Dive</div>
<h1 class="text-3xl font-extrabold text-slate-900">Análise de engajamento por segmento</h1>
<p class="text-sm text-slate-500 mt-2" id="generated"></p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-6">
<div class="card"><div class="stat-label">Respostas</div><div class="stat" id="s-n"></div></div>
<div class="card"><div class="stat-label">Score médio</div><div class="stat" id="s-score"></div></div>
<div class="card"><div class="stat-label">eNPS</div><div class="stat" id="s-enps"></div></div>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Insights</h2>
<ul class="space-y-2" id="insights-list"></ul>
</div>

<div class="grid sm:grid-cols-2 gap-6">
<div class="card"><h2 class="text-xl font-bold mb-4">Por área (ordenado: piores primeiro)</h2><div class="overflow-x-auto"><table><thead><tr><th>Área</th><th>N</th><th>Score</th><th>Min</th><th>Max</th></tr></thead><tbody id="area-tbody"></tbody></table></div></div>
<div class="card"><h2 class="text-xl font-bold mb-4">Por tenure</h2><div class="overflow-x-auto"><table><thead><tr><th>Faixa</th><th>N</th><th>Score</th><th>Min</th><th>Max</th></tr></thead><tbody id="tenure-tbody"></tbody></table></div></div>
<div class="card"><h2 class="text-xl font-bold mb-4">Por nível</h2><div class="overflow-x-auto"><table><thead><tr><th>Nível</th><th>N</th><th>Score</th><th>Min</th><th>Max</th></tr></thead><tbody id="lvl-tbody"></tbody></table></div></div>
<div class="card"><h2 class="text-xl font-bold mb-4">Bottom 10 gestores</h2><div class="overflow-x-auto"><table><thead><tr><th>Gestor</th><th>N</th><th>Score</th></tr></thead><tbody id="mgr-tbody"></tbody></table></div></div>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=engagement-deep-dive" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });
document.getElementById('s-n').textContent = DATA.summary.n_responses;
document.getElementById('s-score').textContent = DATA.summary.overall_score !== null ? DATA.summary.overall_score : '—';
const enpsEl = document.getElementById('s-enps');
const e = DATA.summary.overall_enps;
if (e === null) { enpsEl.textContent = '—'; }
else { enpsEl.textContent = e; enpsEl.className = 'stat ' + (e < 0 ? 'score-bad' : (e < 30 ? 'score-med' : 'score-good')); }

if (DATA.insights.length > 0) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li class="flex items-start"><span class="text-rose-500 font-bold mr-2">●</span><span>${i}</span></li>`).join('');
}

const scoreCls = s => s < 6 ? 'score-bad' : (s < 8 ? 'score-med' : 'score-good');
document.getElementById('area-tbody').innerHTML = DATA.by_area.map(r => `<tr><td><strong>${esc(r.segment)}</strong></td><td>${r.n}</td><td class="${scoreCls(r.avg_score)}">${r.avg_score}</td><td>${r.min_score}</td><td>${r.max_score}</td></tr>`).join('');
document.getElementById('tenure-tbody').innerHTML = DATA.by_tenure.map(r => `<tr><td><strong>${esc(r.segment)}</strong></td><td>${r.n}</td><td class="${scoreCls(r.avg_score)}">${r.avg_score}</td><td>${r.min_score}</td><td>${r.max_score}</td></tr>`).join('');
document.getElementById('lvl-tbody').innerHTML = DATA.by_level.map(r => `<tr><td><strong>${esc(r.segment)}</strong></td><td>${r.n}</td><td class="${scoreCls(r.avg_score)}">${r.avg_score}</td><td>${r.min_score}</td><td>${r.max_score}</td></tr>`).join('');
document.getElementById('mgr-tbody').innerHTML = DATA.bottom_managers.map(r => `<tr><td>${esc(r.manager)}</td><td>${r.n}</td><td class="${scoreCls(r.avg_score)}">${r.avg_score}</td></tr>`).join('');
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
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=engagement-deep-dive")
    return 0


if __name__ == "__main__":
    sys.exit(main())
