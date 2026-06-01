#!/usr/bin/env python3
"""
skills_gap.py — Analisa lacunas de capacidade da força de trabalho contra um
conjunto de capacidades-alvo. Calcula cobertura por skill, magnitude do gap,
prioridade (criticidade × gap) e recomendação build/buy/borrow.

Inputs:
  - Inventory CSV: person, skill, proficiency (1-5)
  - Target CSV: skill, required_proficiency (1-5), criticality (1-5), headcount_needed

Output: HTML executivo com heatmap (skill × criticidade), lista priorizada de
gaps com build/buy/borrow, e resumo de implicações de hiring/training.

Uso:
    python3 skills_gap.py --inventory inv.csv --target target.csv
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

SKILL_NAME = "skills-gap-analysis"
SKILL_VERSION = "1.0.0"


INV_ALIASES = {
    "person":      ["person", "pessoa", "colaborador", "name", "nome"],
    "skill":       ["skill", "competencia", "competência", "habilidade"],
    "proficiency": ["proficiency", "proficiencia", "proficiência", "nivel", "nível", "level", "score"],
}
TARGET_ALIASES = {
    "skill":                ["skill", "competencia", "competência", "habilidade"],
    "required_proficiency": ["required_proficiency", "required", "proficiencia_requerida", "nivel_requerido", "required_level"],
    "criticality":          ["criticality", "criticidade", "importancia", "importância", "priority"],
    "headcount_needed":     ["headcount_needed", "headcount", "hc", "hc_needed", "vagas", "necessario", "necessário"],
}


def _esc(v):
    import html
    return html.escape(str(v), quote=True) if v is not None else ""


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
    s = str(v).strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def recommend(gap, criticality, coverage_ratio):
    """build / buy / borrow.
    BUY: gap grande + alta criticidade (precisa de capacidade nova permanente).
    BORROW: criticidade baixa/média (niche ou temporário) — contractor/parceiro.
    BUILD: gap moderado e já existe base interna (cobertura parcial) — treinar.
    """
    if criticality >= 4 and coverage_ratio < 0.5:
        return ("BUY", "Gap grande em capacidade crítica — contratar é o caminho mais rápido e confiável pra fechar.")
    if coverage_ratio >= 0.5 and gap > 0:
        return ("BUILD", "Já existe base interna parcial — treinar/desenvolver é mais barato e retém conhecimento.")
    if criticality <= 2:
        return ("BORROW", "Capacidade de baixa criticidade ou pontual — contractor/parceiro evita custo fixo.")
    return ("BUILD", "Gap moderado em capacidade relevante — desenvolver internamente com plano de treino.")


def analyze(inventory, target, cols_inv, cols_tgt):
    # cobertura por skill: pessoas com proficiência >= required
    skill_people = defaultdict(list)  # skill -> [(person, prof)]
    for row in inventory:
        skill = (row.get(cols_inv["skill"]) or "").strip()
        prof = _f(row.get(cols_inv["proficiency"]))
        if not skill or prof is None:
            continue
        person = (row.get(cols_inv.get("person") or "") or "—").strip()
        skill_people[_norm(skill)].append({"display": skill, "person": person, "prof": prof})

    gaps = []
    for trow in target:
        skill = (trow.get(cols_tgt["skill"]) or "").strip()
        req = _f(trow.get(cols_tgt["required_proficiency"]))
        crit = _f(trow.get(cols_tgt.get("criticality") or "")) or 3.0
        hc = _f(trow.get(cols_tgt["headcount_needed"])) or 1.0
        if not skill or req is None:
            continue
        crit = max(1.0, min(5.0, crit))
        hc = max(1.0, hc)
        people = skill_people.get(_norm(skill), [])
        covered = sum(1 for p in people if p["prof"] >= req)
        gap = max(0.0, hc - covered)
        coverage_ratio = round(min(1.0, covered / hc), 3) if hc else 0.0
        # prioridade = criticidade × magnitude do gap (normalizado pelo hc)
        gap_magnitude = gap / hc if hc else 0.0
        priority = round(crit * gap_magnitude, 3)
        rec, rationale = recommend(gap, crit, coverage_ratio)
        gaps.append({
            "skill": skill,
            "required": req,
            "criticality": int(crit),
            "headcount_needed": int(hc),
            "covered": covered,
            "gap": int(gap),
            "coverage_pct": round(coverage_ratio * 100, 1),
            "priority": priority,
            "recommendation": rec,
            "rationale": rationale,
        })

    gaps.sort(key=lambda g: (-g["priority"], -g["criticality"], -g["gap"]))

    # heatmap: skill (linha) × criticidade (coluna), valor = gap
    heatmap = [{"skill": g["skill"], "criticality": g["criticality"], "gap": g["gap"],
                "coverage_pct": g["coverage_pct"]} for g in gaps]

    # resumo build/buy/borrow
    bbb = defaultdict(lambda: {"count": 0, "hc": 0})
    total_gap_hc = 0
    for g in gaps:
        if g["gap"] > 0:
            bbb[g["recommendation"]]["count"] += 1
            bbb[g["recommendation"]]["hc"] += g["gap"]
            total_gap_hc += g["gap"]

    insights = []
    open_gaps = [g for g in gaps if g["gap"] > 0]
    if not open_gaps:
        insights.append("Nenhum gap aberto — todas as capacidades-alvo estão cobertas no nível requerido.")
    else:
        buy_hc = bbb.get("BUY", {}).get("hc", 0)
        build_hc = bbb.get("BUILD", {}).get("hc", 0)
        borrow_hc = bbb.get("BORROW", {}).get("hc", 0)
        insights.append(f"<strong>{len(open_gaps)} skill(s)</strong> com gap aberto, somando <strong>{total_gap_hc} posição(ões)</strong> de capacidade a fechar.")
        if buy_hc:
            insights.append(f"<strong>BUY</strong>: ~{buy_hc} contratação(ões) em capacidades críticas com cobertura baixa — priorize requisições.")
        if build_hc:
            insights.append(f"<strong>BUILD</strong>: ~{build_hc} posição(ões) cobríveis via treino/desenvolvimento interno — base parcial já existe.")
        if borrow_hc:
            insights.append(f"<strong>BORROW</strong>: ~{borrow_hc} posição(ões) endereçáveis com contractor/parceiro (baixa criticidade ou pontual).")
        top = open_gaps[0]
        insights.append(f"Maior prioridade: <strong>{_esc(top['skill'])}</strong> (criticidade {top['criticality']}, gap {top['gap']}) → recomendação {top['recommendation']}.")

    return {
        "summary": {
            "skills_evaluated": len(gaps),
            "open_gaps": len(open_gaps),
            "total_gap_hc": total_gap_hc,
            "people_in_inventory": len({(r.get(cols_inv.get("person") or "") or "").strip() for r in inventory if (r.get(cols_inv.get("person") or "") or "").strip()}),
        },
        "gaps": gaps,
        "heatmap": heatmap,
        "build_buy_borrow": {k: bbb[k] for k in ("BUILD", "BUY", "BORROW") if k in bbb},
        "insights": insights,
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>Skills Gap Analysis — Comp</title>
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
  .pill{display:inline-block;padding:.2rem .55rem;border-radius:999px;font-size:.7rem;font-weight:700}
  .rec-BUILD{background:#dbeafe;color:#1e40af}
  .rec-BUY{background:#fee2e2;color:#991b1b}
  .rec-BORROW{background:#fef3c7;color:#92400e}
  .hm-cell{border-radius:6px;padding:.5rem;text-align:center;font-weight:700;font-size:.8rem;color:white}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-6xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Skills Gap Analysis</div>
<h1 class="text-3xl font-extrabold text-slate-900">Lacunas de capacidade · build / buy / borrow</h1>
<p class="text-sm text-slate-500 mt-2" id="generated"></p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
<div class="card"><div class="stat-label">Skills avaliadas</div><div class="stat" id="s-eval"></div></div>
<div class="card"><div class="stat-label">Gaps abertos</div><div class="stat text-rose-600" id="s-open"></div></div>
<div class="card"><div class="stat-label">Posições a fechar</div><div class="stat text-rose-600" id="s-hc"></div></div>
<div class="card"><div class="stat-label">Pessoas no inventário</div><div class="stat" id="s-people"></div></div>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Insights</h2>
<ul class="space-y-2" id="insights-list"></ul>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-1">Heatmap — skill × criticidade</h2>
<p class="text-xs text-slate-500 mb-4">Cor = tamanho do gap (vermelho = gap maior). Coluna = criticidade (1-5).</p>
<div class="overflow-x-auto"><table><thead><tr><th>Skill</th><th>Crit 1</th><th>Crit 2</th><th>Crit 3</th><th>Crit 4</th><th>Crit 5</th></tr></thead><tbody id="hm-tbody"></tbody></table></div>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Gaps priorizados</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Skill</th><th>Prof. req.</th><th>Crit.</th><th>HC alvo</th><th>Cobertos</th><th>Gap</th><th>Cobertura</th><th>Prioridade</th><th>Ação</th><th>Rationale</th></tr></thead><tbody id="gap-tbody"></tbody></table></div>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Implicações de hiring / training</h2>
<div class="grid sm:grid-cols-3 gap-3" id="bbb"></div>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=skills-gap-analysis" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });

document.getElementById('s-eval').textContent = DATA.summary.skills_evaluated;
document.getElementById('s-open').textContent = DATA.summary.open_gaps;
document.getElementById('s-hc').textContent = DATA.summary.total_gap_hc;
document.getElementById('s-people').textContent = DATA.summary.people_in_inventory;

if (DATA.insights.length > 0) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li class="flex items-start"><span class="text-rose-500 font-bold mr-2">●</span><span>${i}</span></li>`).join('');
}

const gapColor = (gap, hc) => {
  if (!gap) return '#e2e8f0';
  const r = hc ? Math.min(1, gap / hc) : 1;
  if (r >= 0.66) return '#dc2626';
  if (r >= 0.34) return '#f59e0b';
  return '#84cc16';
};
document.getElementById('hm-tbody').innerHTML = DATA.heatmap.map(h => {
  let cells = '';
  for (let c = 1; c <= 5; c++) {
    if (c === h.criticality) {
      const bg = gapColor(h.gap, DATA.gaps.find(g => g.skill === h.skill)?.headcount_needed || 1);
      cells += `<td><div class="hm-cell" style="background:${bg}" title="gap ${h.gap}, cobertura ${h.coverage_pct}%">${h.gap}</div></td>`;
    } else {
      cells += `<td></td>`;
    }
  }
  return `<tr><td><strong>${esc(h.skill)}</strong></td>${cells}</tr>`;
}).join('');

document.getElementById('gap-tbody').innerHTML = DATA.gaps.map(g =>
  `<tr><td><strong>${esc(g.skill)}</strong></td><td>${g.required}</td><td>${g.criticality}</td><td>${g.headcount_needed}</td><td>${g.covered}</td><td class="${g.gap > 0 ? 'text-rose-600 font-bold' : ''}">${g.gap}</td><td>${g.coverage_pct}%</td><td>${g.priority}</td><td><span class="pill rec-${g.recommendation}">${esc(g.recommendation)}</span></td><td class="text-slate-500 text-xs">${esc(g.rationale)}</td></tr>`).join('');

const bbbLabels = { BUILD: 'BUILD — treinar', BUY: 'BUY — contratar', BORROW: 'BORROW — contractor/parceiro' };
const bbbClass = { BUILD: 'rec-BUILD', BUY: 'rec-BUY', BORROW: 'rec-BORROW' };
document.getElementById('bbb').innerHTML = ['BUILD','BUY','BORROW'].map(k => {
  const v = DATA.build_buy_borrow[k] || { count: 0, hc: 0 };
  return `<div class="${bbbClass[k]} rounded-lg p-4 text-center"><div class="text-3xl font-bold">${v.hc}</div><div class="text-xs font-semibold mt-1">${bbbLabels[k]}</div><div class="text-xs mt-1">${v.count} skill(s)</div></div>`;
}).join('');
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Análise de lacunas de capacidade (build/buy/borrow).")
    p.add_argument("--inventory", type=Path, required=True, help="CSV: person, skill, proficiency (1-5)")
    p.add_argument("--target", type=Path, required=True, help="CSV: skill, required_proficiency, criticality, headcount_needed")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    headers_i, inventory = load_csv(args.inventory)
    cols_inv = {k: auto_detect(headers_i, INV_ALIASES, k) for k in INV_ALIASES}
    if not cols_inv.get("skill") or not cols_inv.get("proficiency"):
        sys.exit("Inventory precisa de skill + proficiency. Verifique colunas.")

    headers_t, target = load_csv(args.target)
    cols_tgt = {k: auto_detect(headers_t, TARGET_ALIASES, k) for k in TARGET_ALIASES}
    if not cols_tgt.get("skill") or not cols_tgt.get("required_proficiency") or not cols_tgt.get("headcount_needed"):
        sys.exit("Target precisa de skill + required_proficiency + headcount_needed. Verifique colunas.")

    print(f"Inventory: {len(inventory)} linhas | Target: {len(target)} skills")
    data = analyze(inventory, target, cols_inv, cols_tgt)
    out = args.output or Path.cwd() / f"skills-gap-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    print(f"  {data['summary']['open_gaps']} gaps abertos | {data['summary']['total_gap_hc']} posições a fechar")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=skills-gap-analysis")
    return 0


if __name__ == "__main__":
    sys.exit(main())
