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
<title>Span of Intelligence Diagnostic · Zivo</title>
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
  .soi-traditional{background:rgba(26,26,26,.05);color:#1A1A1A}
  .soi-hybrid{background:#E7F1FF;color:#0B58BB}
  .soi-orchestration{background:#DDF7EA;color:#0B7A43}
  .soi-underutilized{background:#FFF2DA;color:#985704}
  .soi-overloaded_legacy{background:#FEE7EA;color:#B3172A}
  .soi-tile{background:#FFFFFF;border:1px solid rgba(26,26,26,.1);padding:20px;min-width:0}
  .soi-tile .pill{white-space:normal}
  .page tbody tr:hover{background:rgba(26,26,26,.05)}
</style></head>
<body>
<header class="hero"><div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>Span of intelligence</span><span><span id="generated"></span></span><span>Confidencial</span></div>
<h1>Diagnóstico organizacional</h1>
<p class="hero-sub">Da quantidade de diretos pra inteligência que o time gera. Baseado no artigo da <a href="https://cajuina.org/principais/coluna-comp/de-span-of-control-a-span-of-intelligence/?utm_source=skill-output&utm_medium=html-link&utm_campaign=eam&utm_content=span-of-control-diagnostic" target="_blank">coluna Zivo na Cajuína</a>.</p>
</div></header>
<main class="page">

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
<div class="card"><div class="stat-label">Colaboradores</div><div class="stat" id="s-total"></div></div>
<div class="card"><div class="stat-label">Gestores</div><div class="stat" id="s-managers"></div></div>
<div class="card"><div class="stat-label">ICs</div><div class="stat" id="s-ics"></div></div>
<div class="card"><div class="stat-label">Camadas</div><div class="stat" id="s-layers"></div></div>
</div>

<div class="card">
<h2 style="margin-bottom:8px">Classificação Span of Intelligence</h2>
<p class="text-sm text-zv-ink80 mb-4">Cada gestor classificado pela combinação de span tradicional + presença de IA + automação.</p>
<div class="grid grid-cols-2 sm:grid-cols-5 gap-3" id="soi-dist"></div>
</div>

<div class="card" id="recs-card" style="display:none;">
<h2>Recomendações</h2>
<ul class="space-y-3 zv-list" id="recs-list"></ul>
</div>

<div class="card">
<h2>Por área</h2>
<div class="overflow-x-auto"><table>
<thead><tr><th>Área</th><th>HC</th><th>Gestores</th><th>Span médio</th><th>Agentes IA</th><th>Automação média</th></tr></thead>
<tbody id="areas-tbody"></tbody></table></div>
</div>

<div class="card">
<h2>Top 10 spans (com classificação SoI)</h2>
<div class="overflow-x-auto"><table>
<thead><tr><th>Gestor</th><th>Área</th><th>Diretos</th><th>Agentes</th><th>Auto%</th><th>Span ajustado</th><th>Classificação</th></tr></thead>
<tbody id="top-tbody"></tbody></table></div>
</div>

</main>
<footer class="site-footer">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=span-of-control-diagnostic" aria-label="Zivo"><svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg></a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer>

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
  return `<div class="soi-tile">
    <div class="stat" style="margin-top:0">${n}</div>
    <div class="mt-2"><span class="pill ${soiColors[k]}">${soiLabels[k]}</span></div>
  </div>`;
}).join('');

if (DATA.recommendations.length > 0) {
  document.getElementById('recs-card').style.display = '';
  document.getElementById('recs-list').innerHTML = DATA.recommendations.map(r =>
    `<li class="flex items-start"><i class="zv-dot"></i><span>${r}</span></li>`).join('');
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

    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=span-of-control-diagnostic")
    return 0


if __name__ == "__main__":
    sys.exit(main())
