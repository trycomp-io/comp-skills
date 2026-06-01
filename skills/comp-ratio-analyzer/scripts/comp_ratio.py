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
<meta charset="UTF-8"><title>Comp Ratio Analysis — Comp</title>
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
  .band-under{background:#fee2e2;color:#991b1b}
  .band-below{background:#fef3c7;color:#92400e}
  .band-at{background:#d1fae5;color:#065f46}
  .band-above{background:#dbeafe;color:#1e40af}
  .band-over{background:#fae8ff;color:#86198f}
  .pill{display:inline-block;padding:.2rem .55rem;border-radius:999px;font-size:.7rem;font-weight:600}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-6xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Comp Ratio Analysis</div>
<h1 class="text-3xl font-extrabold text-slate-900">Distribuição salarial vs bandas</h1>
<p class="text-sm text-slate-500 mt-2" id="generated"></p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
<div class="card"><div class="stat-label">Analisados</div><div class="stat" id="s-analyzed"></div></div>
<div class="card"><div class="stat-label">Roster total</div><div class="stat" id="s-total"></div></div>
<div class="card"><div class="stat-label">Custo equalizar (mensal)</div><div class="stat text-rose-600" id="s-cost"></div></div>
<div class="card"><div class="stat-label">Anual c/ encargos</div><div class="stat text-rose-600" id="s-cost-y"></div></div>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Distribuição</h2>
<div class="grid sm:grid-cols-5 gap-3" id="dist"></div>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Insights</h2>
<ul class="space-y-2" id="insights-list"></ul>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Por nível</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Nível</th><th>HC</th><th>Compa ratio médio</th><th>Min</th><th>Max</th></tr></thead><tbody id="lvl-tbody"></tbody></table></div>
</div>

<div class="grid sm:grid-cols-2 gap-6">
<div class="card"><h2 class="text-xl font-bold mb-4">Top 10 under-paid</h2><div class="overflow-x-auto"><table><thead><tr><th>Nome</th><th>Nível</th><th>Salário</th><th>Mediana</th><th>Ratio</th><th>Gap</th></tr></thead><tbody id="under-tbody"></tbody></table></div></div>
<div class="card"><h2 class="text-xl font-bold mb-4">Top 10 over-paid</h2><div class="overflow-x-auto"><table><thead><tr><th>Nome</th><th>Nível</th><th>Salário</th><th>Mediana</th><th>Ratio</th><th>Gap</th></tr></thead><tbody id="over-tbody"></tbody></table></div></div>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=comp-ratio-analyzer" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });
const fmt = v => 'R$ ' + v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

document.getElementById('s-analyzed').textContent = DATA.summary.total_analyzed;
document.getElementById('s-total').textContent = DATA.summary.total_roster;
document.getElementById('s-cost').textContent = fmt(DATA.summary.cost_monthly_to_mid);
document.getElementById('s-cost-y').textContent = fmt(DATA.summary.cost_annual_loaded);

const distLabels = { under: '<80% Under', below: '80-95% Below', at: '95-105% At Target', above: '105-120% Above', over: '>120% Over' };
const distClass = { under: 'band-under', below: 'band-below', at: 'band-at', above: 'band-above', over: 'band-over' };
document.getElementById('dist').innerHTML = ['under','below','at','above','over'].map(k =>
  `<div class="${distClass[k]} rounded-lg p-4 text-center">
    <div class="text-3xl font-bold">${DATA.distribution[k] || 0}</div>
    <div class="text-xs font-semibold mt-1">${distLabels[k]}</div>
  </div>`).join('');

if (DATA.insights.length > 0) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li class="flex items-start"><span class="text-rose-500 font-bold mr-2">●</span><span>${i}</span></li>`).join('');
}

document.getElementById('lvl-tbody').innerHTML = DATA.by_level.map(l =>
  `<tr><td><strong>${esc(l.level)}</strong></td><td>${l.total}</td><td>${l.avg_ratio}</td><td>${l.min_ratio}</td><td>${l.max_ratio}</td></tr>`).join('');

document.getElementById('under-tbody').innerHTML = DATA.under_outliers.map(c =>
  `<tr><td>${esc(c.name)}</td><td>${esc(c.level)}</td><td>${fmt(c.salary)}</td><td>${fmt(c.mid)}</td><td><span class="pill ${distClass[c.class]}">${c.ratio}</span></td><td class="text-rose-600">${fmt(c.delta_to_mid)}</td></tr>`).join('');
document.getElementById('over-tbody').innerHTML = DATA.over_outliers.map(c =>
  `<tr><td>${esc(c.name)}</td><td>${esc(c.level)}</td><td>${fmt(c.salary)}</td><td>${fmt(c.mid)}</td><td><span class="pill ${distClass[c.class]}">${c.ratio}</span></td><td class="text-emerald-600">+${fmt(c.delta_to_mid)}</td></tr>`).join('');
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


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
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=comp-ratio-analyzer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
