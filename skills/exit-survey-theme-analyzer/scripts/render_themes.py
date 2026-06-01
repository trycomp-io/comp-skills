#!/usr/bin/env python3
"""
render_themes.py — Renderiza um relatório HTML a partir de um JSON de temas
produzido pela análise qualitativa (feita pelo agente/LLM, NÃO por este script).

Este script NÃO faz NLP. Ele apenas renderiza o JSON de temas no formato:

{
  "total_comments": 87,
  "period": "Q1 2026",
  "themes": [
    {
      "name": "Remuneração",
      "count": 24,
      "pct": 27.6,
      "sentiment": "negativo",          // negativo | neutro | positivo
      "quotes": ["...", "..."],          // citações JÁ anonimizadas
      "recommended_actions": ["...", "..."]
    }
  ],
  "segments": [                          // opcional, cross-tab por segmento
    {"segment": "Engenharia", "theme": "Remuneração", "count": 9}
  ],
  "rising_negative": ["Carga de trabalho"],  // opcional, temas em alta negativa
  "notes": ["Células com <3 comentários suprimidas."]  // opcional
}

Uso:
    cat themes.json | python3 render_themes.py
    python3 render_themes.py --input themes.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "exit-survey-theme-analyzer"
SKILL_VERSION = "1.0.0"


def normalize(d):
    """Garante estrutura mínima e ordena temas por frequência desc."""
    themes = d.get("themes") or []
    for t in themes:
        t.setdefault("count", 0)
        t.setdefault("pct", 0)
        t.setdefault("sentiment", "neutro")
        t.setdefault("quotes", [])
        t.setdefault("recommended_actions", [])
    themes.sort(key=lambda t: -(t.get("count") or 0))
    return {
        "total_comments": d.get("total_comments", sum(t.get("count", 0) for t in themes)),
        "period": d.get("period", ""),
        "themes": themes,
        "segments": d.get("segments") or [],
        "rising_negative": d.get("rising_negative") or [],
        "notes": d.get("notes") or [],
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>Exit Survey Theme Analysis — Comp</title>
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
  .quote{font-style:italic;color:#475569;border-left:3px solid #cbd5e1;padding-left:.75rem;margin:.4rem 0;font-size:.85rem}
  .sent-negativo{background:#fee2e2;color:#991b1b}
  .sent-neutro{background:#f1f5f9;color:#475569}
  .sent-positivo{background:#d1fae5;color:#065f46}
  .pill{display:inline-block;padding:.2rem .6rem;border-radius:999px;font-size:.72rem;font-weight:700}
  .bar{height:10px;border-radius:999px;background:#e2e8f0;overflow:hidden}
  .bar > span{display:block;height:100%}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-5xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Theme Analysis</div>
<h1 class="text-3xl font-extrabold text-slate-900">Temas em comentários abertos</h1>
<p class="text-sm text-slate-500 mt-2" id="generated"></p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-6">
<div class="card"><div class="stat-label">Comentários</div><div class="stat" id="s-total"></div></div>
<div class="card"><div class="stat-label">Temas</div><div class="stat" id="s-themes"></div></div>
<div class="card"><div class="stat-label">Período</div><div class="stat text-base pt-3" id="s-period"></div></div>
</div>

<div class="card" id="rising-card" style="display:none;">
<h2 class="text-lg font-bold mb-2 text-rose-700">Temas em alta negativa</h2>
<div id="rising-list" class="flex flex-wrap gap-2"></div>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Temas (ranking por frequência)</h2>
<div id="themes-list" class="space-y-5"></div>
</div>

<div class="card" id="seg-card" style="display:none;">
<h2 class="text-xl font-bold mb-1">Padrões por segmento</h2>
<p class="text-xs text-slate-500 mb-4">Células com menos de 3 comentários são suprimidas para preservar anonimato.</p>
<div class="overflow-x-auto"><table><thead><tr><th>Segmento</th><th>Tema</th><th>Comentários</th></tr></thead><tbody id="seg-tbody"></tbody></table></div>
</div>

<div class="card" id="notes-card" style="display:none;">
<h2 class="text-sm font-bold mb-2 text-slate-500 uppercase">Notas metodológicas</h2>
<ul class="text-xs text-slate-500 space-y-1 list-disc pl-5" id="notes-list"></ul>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=exit-survey-theme-analyzer" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });

document.getElementById('s-total').textContent = DATA.total_comments;
document.getElementById('s-themes').textContent = DATA.themes.length;
document.getElementById('s-period').textContent = DATA.period || '—';

const sentClass = { negativo: 'sent-negativo', neutro: 'sent-neutro', positivo: 'sent-positivo' };
const sentBar = { negativo: '#dc2626', neutro: '#94a3b8', positivo: '#10b981' };

if (DATA.rising_negative.length > 0) {
  document.getElementById('rising-card').style.display = '';
  document.getElementById('rising-list').innerHTML = DATA.rising_negative.map(r =>
    `<span class="pill sent-negativo">${esc(r)}</span>`).join('');
}

document.getElementById('themes-list').innerHTML = DATA.themes.map(t => {
  const sc = sentClass[t.sentiment] || 'sent-neutro';
  const bc = sentBar[t.sentiment] || '#94a3b8';
  const quotes = (t.quotes || []).map(q => `<div class="quote">${esc(q)}</div>`).join('');
  const actions = (t.recommended_actions || []).length
    ? `<div class="mt-2 text-sm"><strong>Ações:</strong><ul class="list-disc pl-5 mt-1">${t.recommended_actions.map(a => `<li>${esc(a)}</li>`).join('')}</ul></div>`
    : '';
  return `<div>
    <div class="flex justify-between items-center mb-1">
      <div class="font-bold text-slate-800">${esc(t.name)} <span class="text-slate-400 font-normal">· ${t.count} (${t.pct}%)</span></div>
      <span class="pill ${sc}">${esc(t.sentiment)}</span>
    </div>
    <div class="bar"><span style="width:${Math.min(100, t.pct)}%;background:${bc}"></span></div>
    ${quotes}
    ${actions}
  </div>`;
}).join('');

if (DATA.segments.length > 0) {
  document.getElementById('seg-card').style.display = '';
  document.getElementById('seg-tbody').innerHTML = DATA.segments.map(s =>
    `<tr><td><strong>${esc(s.segment)}</strong></td><td>${esc(s.theme)}</td><td>${s.count}</td></tr>`).join('');
}

if (DATA.notes.length > 0) {
  document.getElementById('notes-card').style.display = '';
  document.getElementById('notes-list').innerHTML = DATA.notes.map(n => `<li>${esc(n)}</li>`).join('');
}
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Renderiza relatório HTML de temas (qualitative theme analysis).")
    p.add_argument("--input", type=Path, help="JSON de temas (senão, lê do stdin)")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    if args.input:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        if sys.stdin.isatty():
            sys.exit("Forneça --input <file> ou pipe o JSON de temas via stdin.")
        raw = json.loads(sys.stdin.read())

    data = normalize(raw)
    out = args.output or Path.cwd() / f"theme-analysis-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    print(f"  {len(data['themes'])} temas | {data['total_comments']} comentários")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=exit-survey-theme-analyzer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
