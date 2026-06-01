#!/usr/bin/env python3
"""
span_analysis.py — Diagnóstico de Span of Intelligence (evolução do span of control).

Baseado no artigo Cajuína "De Span of Control a Span of Intelligence":
https://cajuina.org/principais/coluna-comp/de-span-of-control-a-span-of-intelligence/

Input: CSV/XLSX com no mínimo 3 colunas lógicas (auto-detect em PT/EN):
  - employee_id, name, manager_id  (estrutura básica)
Opcionais (ativam análise Span of Intelligence completa):
  - area, level
  - ai_agents      — nº de agentes IA dedicados a esse gestor/time
  - automation_pct — % do trabalho do time já automatizado (0-100)
  - complexity     — low / medium / high

Output: relatório HTML com:
- Span tradicional (diretos) por gestor
- Span ajustado por automação (quando dados disponíveis)
- Classificação Span of Intelligence: Tradicional / Híbrido / Orquestração / Subutilizado
- Recomendações reframed (não "quebre time", e sim "automatize ou senior-ize")
- Identifica lacuna de dados pra análise completa

Privacy: 100% local.

Uso:
    python3 span_analysis.py --input org.csv
    python3 span_analysis.py --input org.csv --area-col Departamento
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

SKILL_NAME = "span-of-control-diagnostic"
SKILL_VERSION = "1.0.0"


# ========== Column detection ==========

ALIASES = {
    "employee_id":    ["employee_id", "id", "matricula", "matrícula", "user_id", "person_id"],
    "name":           ["name", "nome", "colaborador", "employee", "funcionario", "funcionário", "full_name"],
    "manager_id":     ["manager_id", "manager", "gestor", "gestor_id", "lider", "líder", "lider_id", "reports_to", "boss_id"],
    "area":           ["area", "área", "departamento", "department", "função", "business_unit", "bu", "team"],
    "level":          ["level", "nivel", "nível", "job_level", "cargo_level", "senioridade", "seniority"],
    "ai_agents":      ["ai_agents", "agentes_ia", "agentes", "ai_count", "agents"],
    "automation_pct": ["automation_pct", "automation", "automacao_pct", "automação_pct", "pct_automatizado"],
    "complexity":     ["complexity", "complexidade"],
}


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").strip().lower().replace(" ", "_")


def auto_detect(headers: list[str], key: str) -> str | None:
    norm_h = {_norm(h): h for h in headers}
    for cand in ALIASES[key]:
        if _norm(cand) in norm_h:
            return norm_h[_norm(cand)]
    return None


def load_csv(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def load_xlsx(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    try:
        import openpyxl  # type: ignore
    except ImportError:
        sys.exit("Excel input requer openpyxl. Instale com: pip install openpyxl")
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    headers = [str(h) if h is not None else "" for h in next(it)]
    rows = []
    for r in it:
        rows.append({headers[i]: r[i] for i in range(len(headers))})
    return headers, rows


def _to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ========== Span of Intelligence classification ==========


def classify_soi(directs: int, ai_agents: int, automation_pct: float) -> tuple[str, str]:
    """
    Retorna (categoria, recomendação_curta).

    Categorias:
    - traditional: humanos puros, sem IA, span normal
    - hybrid: alguma IA + humanos
    - orchestration: IA dominante (2+ agentes ou automation >60%)
    - underutilized: span <4 sem IA → oportunidade de senior-izar
    - overloaded_legacy: span >12 sem IA → urgente avaliar IA antes de splitting
    """
    if directs < 4 and ai_agents == 0 and automation_pct < 20:
        return "underutilized", "Span baixo sem IA — avalie se cabe senior-izar (eliminar camada ou virar IC sênior)."
    if ai_agents >= 2 or automation_pct >= 60:
        return "orchestration", "Time AI-native — gestor já é orquestrador. Mensure inteligência gerada, não horas."
    if ai_agents >= 1 or automation_pct >= 20:
        return "hybrid", "Estrutura híbrida em transição. Identifique próximas tarefas pra agentificar."
    if directs > 12:
        return "overloaded_legacy", "Span alto e zero IA — antes de quebrar o time, avalie quais tarefas operacionais um agente pode absorver."
    return "traditional", "Estrutura tradicional. Reserve oportunidade pra híbrido quando o tipo de trabalho permitir."


def analyze(rows: list[dict[str, Any]], cols: dict[str, str | None]) -> dict[str, Any]:
    employees: dict[str, dict[str, Any]] = {}
    has_ai_data = bool(cols.get("ai_agents") or cols.get("automation_pct"))

    for row in rows:
        eid = str(row.get(cols["employee_id"]) or "").strip()
        if not eid:
            continue
        name = str(row.get(cols["name"]) or eid).strip()
        mid = str(row.get(cols["manager_id"]) or "").strip()
        area = (str(row.get(cols["area"]) or "—").strip() if cols.get("area") else "—")
        level = (str(row.get(cols["level"]) or "—").strip() if cols.get("level") else "—")
        ai_agents = int(_to_float(row.get(cols["ai_agents"])) or 0) if cols.get("ai_agents") else 0
        auto_pct = _to_float(row.get(cols["automation_pct"])) if cols.get("automation_pct") else 0.0
        if auto_pct is None:
            auto_pct = 0.0
        complexity = (str(row.get(cols["complexity"]) or "").strip().lower() if cols.get("complexity") else "")

        employees[eid] = {
            "id": eid, "name": name, "manager_id": mid or None,
            "area": area, "level": level, "directs": [],
            "ai_agents": ai_agents, "automation_pct": auto_pct, "complexity": complexity,
        }

    for emp in employees.values():
        if emp["manager_id"] and emp["manager_id"] in employees:
            employees[emp["manager_id"]]["directs"].append(emp["id"])

    managers = [e for e in employees.values() if len(e["directs"]) > 0]
    ics = [e for e in employees.values() if len(e["directs"]) == 0]

    # Per-manager SoI classification
    for m in managers:
        directs_count = len(m["directs"])
        cat, rec = classify_soi(directs_count, m["ai_agents"], m["automation_pct"])
        m["soi_category"] = cat
        m["soi_rec"] = rec
        m["adjusted_span"] = round(directs_count * (1 - m["automation_pct"] / 100), 1)

    # Distribution by SoI category
    soi_dist = defaultdict(int)
    for m in managers:
        soi_dist[m["soi_category"]] += 1

    # Layers
    roots = [e for e in employees.values() if not e["manager_id"] or e["manager_id"] not in employees]

    def depth(eid: str, seen: set, d: int) -> int:
        if eid in seen:
            return d
        seen.add(eid)
        emp = employees[eid]
        if not emp["directs"]:
            return d
        return max(depth(c, seen, d + 1) for c in emp["directs"])

    max_layers = 0
    for root in roots:
        max_layers = max(max_layers, depth(root["id"], set(), 1))

    top_spans = sorted(managers, key=lambda m: len(m["directs"]), reverse=True)[:10]

    # Area summary
    area_summary = defaultdict(lambda: {"headcount": 0, "managers": 0, "spans": [], "ai_total": 0, "auto_avg": []})
    for emp in employees.values():
        area_summary[emp["area"]]["headcount"] += 1
        if len(emp["directs"]) > 0:
            area_summary[emp["area"]]["managers"] += 1
            area_summary[emp["area"]]["spans"].append(len(emp["directs"]))
            area_summary[emp["area"]]["ai_total"] += emp["ai_agents"]
            if emp["automation_pct"] > 0:
                area_summary[emp["area"]]["auto_avg"].append(emp["automation_pct"])

    area_rows = []
    for area, s in area_summary.items():
        spans = s["spans"]
        area_rows.append({
            "area": area, "headcount": s["headcount"], "managers": s["managers"],
            "avg_span": round(sum(spans) / len(spans), 1) if spans else 0,
            "ai_agents_total": s["ai_total"],
            "automation_avg_pct": round(sum(s["auto_avg"]) / len(s["auto_avg"]), 1) if s["auto_avg"] else 0,
        })
    area_rows.sort(key=lambda r: r["headcount"], reverse=True)

    # Recommendations
    recs = []
    overloaded = [m for m in managers if m["soi_category"] == "overloaded_legacy"]
    if overloaded:
        recs.append(f"<strong>{len(overloaded)} gestor(es) com span >12 e zero IA</strong>. Em vez de quebrar essas equipes, avalie quais tarefas operacionais podem virar agentes — ganho de capacidade sem custo organizacional.")
    underutil = [m for m in managers if m["soi_category"] == "underutilized"]
    if underutil:
        recs.append(f"<strong>{len(underutil)} gestor(es) com span <4 sem automação</strong>. Estrutura tradicional pede senior-ização — eliminar camadas ou converter gestor em IC sênior libera headcount.")
    if max_layers > 6:
        recs.append(f"<strong>{max_layers} camadas</strong> é sinal de organização ainda em mindset de span of control. A tese do artigo: estruturas tendem a achatar quando IA absorve transacional. Mapeie próximas tarefas pra agentificar.")
    if not has_ai_data:
        recs.append("<strong>Dados de IA não fornecidos</strong>. Pra análise completa de Span of Intelligence, adicione colunas <code>ai_agents</code> e <code>automation_pct</code> ao CSV — o skill ajusta a classificação automaticamente.")

    return {
        "summary": {
            "total_employees": len(employees),
            "managers": len(managers),
            "ics": len(ics),
            "max_layers": max_layers,
            "has_ai_data": has_ai_data,
            "n_roots": len(roots),
        },
        "soi_distribution": dict(soi_dist),
        "top_spans": [{
            "name": m["name"], "area": m["area"], "directs": len(m["directs"]),
            "ai_agents": m["ai_agents"], "automation_pct": m["automation_pct"],
            "adjusted_span": m["adjusted_span"], "soi_category": m["soi_category"],
        } for m in top_spans],
        "areas": area_rows,
        "recommendations": recs,
    }


# ========== HTML ==========


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Span of Intelligence Diagnostic — Comp</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  body{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b}
  .card{background:white;border-radius:12px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin-bottom:1.5rem}
  .stat{font-size:2.25rem;font-weight:800;color:#0f172a}
  .stat-label{font-size:.875rem;color:#64748b;text-transform:uppercase;letter-spacing:.05em;font-weight:600}
  .soi-traditional{background:#e0e7ff;color:#3730a3}
  .soi-hybrid{background:#dbeafe;color:#1e40af}
  .soi-orchestration{background:#d1fae5;color:#065f46}
  .soi-underutilized{background:#fef3c7;color:#92400e}
  .soi-overloaded_legacy{background:#fee2e2;color:#991b1b}
  table{width:100%;border-collapse:collapse;font-size:.875rem}
  th{background:#1e293b;color:white;padding:.75rem;text-align:left;font-weight:600}
  td{padding:.75rem;border-bottom:1px solid #e2e8f0}
  tr:hover{background:#f8fafc}
  .pill{display:inline-block;padding:.25rem .65rem;border-radius:999px;font-size:.7rem;font-weight:600}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-6xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Span of Intelligence</div>
<h1 class="text-3xl font-extrabold text-slate-900">Diagnóstico organizacional</h1>
<p class="text-slate-600 mt-1">Da quantidade de diretos pra inteligência que o time gera. Baseado no artigo da <a href="https://cajuina.org/principais/coluna-comp/de-span-of-control-a-span-of-intelligence/?utm_source=skill-output&utm_medium=html-link&utm_campaign=eam&utm_content=span-of-control-diagnostic" target="_blank" class="text-rose-600 font-semibold hover:underline">coluna Comp na Cajuína</a>.</p>
<p class="text-sm text-slate-500 mt-2" id="generated"></p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
<div class="card"><div class="stat-label">Colaboradores</div><div class="stat" id="s-total"></div></div>
<div class="card"><div class="stat-label">Gestores</div><div class="stat" id="s-managers"></div></div>
<div class="card"><div class="stat-label">ICs</div><div class="stat" id="s-ics"></div></div>
<div class="card"><div class="stat-label">Camadas</div><div class="stat" id="s-layers"></div></div>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-2">Classificação Span of Intelligence</h2>
<p class="text-sm text-slate-600 mb-4">Cada gestor classificado pela combinação de span tradicional + presença de IA + automação.</p>
<div class="grid sm:grid-cols-5 gap-3" id="soi-dist"></div>
</div>

<div class="card" id="recs-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Recomendações</h2>
<ul class="space-y-3" id="recs-list"></ul>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Por área</h2>
<div class="overflow-x-auto"><table>
<thead><tr><th>Área</th><th>HC</th><th>Gestores</th><th>Span médio</th><th>Agentes IA</th><th>Automação média</th></tr></thead>
<tbody id="areas-tbody"></tbody></table></div>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Top 10 spans (com classificação SoI)</h2>
<div class="overflow-x-auto"><table>
<thead><tr><th>Gestor</th><th>Área</th><th>Diretos</th><th>Agentes</th><th>Auto%</th><th>Span ajustado</th><th>Classificação</th></tr></thead>
<tbody id="top-tbody"></tbody></table></div>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=span-of-control-diagnostic" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
const today = new Date().toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' });
document.getElementById('generated').textContent = 'Gerado em ' + today;
document.getElementById('s-total').textContent = DATA.summary.total_employees;
document.getElementById('s-managers').textContent = DATA.summary.managers;
document.getElementById('s-ics').textContent = DATA.summary.ics;
document.getElementById('s-layers').textContent = DATA.summary.max_layers;

const soiLabels = {
  traditional: 'Tradicional', hybrid: 'Híbrido', orchestration: 'Orquestração',
  underutilized: 'Subutilizado', overloaded_legacy: 'Sobrecarregado (sem IA)',
};
const soiColors = {
  traditional: 'soi-traditional', hybrid: 'soi-hybrid', orchestration: 'soi-orchestration',
  underutilized: 'soi-underutilized', overloaded_legacy: 'soi-overloaded_legacy',
};
document.getElementById('soi-dist').innerHTML = ['traditional','hybrid','orchestration','underutilized','overloaded_legacy'].map(k => {
  const n = DATA.soi_distribution[k] || 0;
  return `<div class="${soiColors[k]} rounded-lg p-4 text-center">
    <div class="text-3xl font-bold">${n}</div>
    <div class="text-xs font-semibold mt-1">${soiLabels[k]}</div>
  </div>`;
}).join('');

if (DATA.recommendations.length > 0) {
  document.getElementById('recs-card').style.display = '';
  document.getElementById('recs-list').innerHTML = DATA.recommendations.map(r =>
    `<li class="flex items-start"><span class="text-rose-500 font-bold mr-2">●</span><span>${r}</span></li>`).join('');
}

document.getElementById('areas-tbody').innerHTML = DATA.areas.map(a =>
  `<tr><td><strong>${esc(a.area)}</strong></td><td>${a.headcount}</td><td>${a.managers}</td><td>${a.avg_span}</td><td>${a.ai_agents_total}</td><td>${a.automation_avg_pct}%</td></tr>`).join('');

document.getElementById('top-tbody').innerHTML = DATA.top_spans.map(m =>
  `<tr><td>${esc(m.name)}</td><td>${esc(m.area)}</td><td><strong>${m.directs}</strong></td><td>${m.ai_agents}</td><td>${m.automation_pct}%</td><td>${m.adjusted_span}</td><td><span class="pill ${soiColors[m.soi_category]}">${soiLabels[m.soi_category]}</span></td></tr>`).join('');
</script>
</body></html>
"""


def render_html(data: dict, output_path: Path) -> None:
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("__DATA__", payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


# ========== CLI ==========


def main() -> int:
    p = argparse.ArgumentParser(description="Diagnóstico de Span of Intelligence (CSV/XLSX → HTML).")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--employee-id-col")
    p.add_argument("--name-col")
    p.add_argument("--manager-id-col")
    p.add_argument("--area-col")
    p.add_argument("--level-col")
    p.add_argument("--ai-agents-col")
    p.add_argument("--automation-pct-col")
    p.add_argument("--complexity-col")
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    ext = args.input.suffix.lower()
    if ext == ".csv":
        headers, rows = load_csv(args.input)
    elif ext in (".xlsx", ".xlsm"):
        headers, rows = load_xlsx(args.input)
    else:
        sys.exit(f"Formato não suportado: {ext}")

    cols = {}
    for key in ALIASES:
        override = getattr(args, f"{key.replace('_id', '_id')}_col", None)
        cols[key] = override or auto_detect(headers, key)

    missing = [k for k in ("employee_id", "name", "manager_id") if not cols[k]]
    if missing:
        sys.exit(f"Colunas obrigatórias não detectadas: {missing}. Use --{missing[0].replace('_','-')}-col.")

    print(f"Colunas: id={cols['employee_id']!r} name={cols['name']!r} manager={cols['manager_id']!r}")
    if cols.get("ai_agents") or cols.get("automation_pct"):
        print(f"  AI cols: ai_agents={cols.get('ai_agents')!r} automation={cols.get('automation_pct')!r}")
    print(f"Rows: {len(rows)}")

    data = analyze(rows, cols)
    out = args.output or Path.cwd() / f"span-of-intelligence-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    print(f"  HC: {data['summary']['total_employees']} · Gestores: {data['summary']['managers']} · Camadas: {data['summary']['max_layers']}")
    if not data['summary']['has_ai_data']:
        print("  Nota: análise sem dados de IA. Adicione colunas ai_agents/automation_pct pra Span of Intelligence completo.")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=span-of-control-diagnostic")
    return 0


if __name__ == "__main__":
    sys.exit(main())
