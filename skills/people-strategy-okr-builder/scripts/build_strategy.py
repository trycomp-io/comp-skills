#!/usr/bin/env python3
"""
build_strategy.py — Renderiza um one-pager HTML da estratégia de People + OKRs
amarrados à estratégia de negócio, a partir de um JSON de estratégia.

Este script NÃO inventa conteúdo — ele renderiza o JSON que o agente monta
após coletar os inputs conversacionalmente (estratégia de negócio, dores de
people, contexto de headcount, horizonte, restrições).

Estrutura do JSON:

{
  "title": "People Strategy 2026",
  "owner": "CHRO",
  "horizon": "Anual",
  "business_context": "...",
  "priorities": [
    {
      "name": "Escalar engenharia sem perder qualidade de contratação",
      "business_goal": "Dobrar o time de produto no H2",
      "objective": "...",
      "key_results": [
        {"kr": "Reduzir time-to-hire de 60 para 35 dias", "target": "35 dias", "metric": "time-to-hire"}
      ],
      "initiatives": ["...", "..."],
      "owner": "Head de Talent",
      "metric": "time-to-hire"
    }
  ],
  "risks": ["..."],
  "dependencies": ["..."],
  "roadmap": [
    {"quarter": "Q1", "milestones": ["...", "..."]}
  ]
}

Uso:
    cat strategy.json | python3 build_strategy.py
    python3 build_strategy.py --input strategy.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "people-strategy-okr-builder"
SKILL_VERSION = "1.0.0"


def _slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip()).strip("-").lower()[:50] or "people-strategy"


def normalize(d):
    pr = d.get("priorities") or []
    for p in pr:
        p.setdefault("key_results", [])
        p.setdefault("initiatives", [])
        kr = p.get("key_results") or []
        for k in kr:
            if isinstance(k, str):
                continue
            k.setdefault("target", "")
            k.setdefault("metric", "")
    return {
        "title": d.get("title", "People Strategy"),
        "owner": d.get("owner", ""),
        "horizon": d.get("horizon", "Anual"),
        "business_context": d.get("business_context", ""),
        "priorities": pr,
        "risks": d.get("risks") or [],
        "dependencies": d.get("dependencies") or [],
        "roadmap": d.get("roadmap") or [],
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>People Strategy — Comp</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  body{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b;line-height:1.55}
  .wrap{max-width:1000px;margin:0 auto}
  .card{background:white;border-radius:12px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin-bottom:1.5rem}
  .priority{border:1px solid #e2e8f0;border-radius:10px;padding:1.25rem;background:#fafbfc;margin-bottom:1rem}
  .badge{display:inline-block;background:#fee2e2;color:#991b1b;font-size:.7rem;font-weight:700;padding:.2rem .6rem;border-radius:999px;text-transform:uppercase}
  .kr{background:white;border:1px solid #e2e8f0;border-radius:8px;padding:.6rem .85rem;margin:.4rem 0;display:flex;justify-content:space-between;gap:1rem;align-items:center}
  .kr-target{font-weight:700;color:#0f172a;white-space:nowrap;background:#dbeafe;padding:.15rem .55rem;border-radius:6px;font-size:.8rem}
  ul{list-style:disc;padding-left:1.4rem}
  .rail{display:flex;gap:1rem;overflow-x:auto;padding-bottom:.5rem}
  .q{min-width:200px;flex:1;background:white;border:1px solid #e2e8f0;border-top:4px solid #ff4456;border-radius:8px;padding:1rem}
  .q-name{font-weight:800;color:#0f172a;margin-bottom:.5rem}
</style></head>
<body class="p-6 sm:p-10"><div class="wrap">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">People Strategy on a Page</div>
<h1 class="text-3xl font-extrabold text-slate-900" id="title"></h1>
<p class="text-sm text-slate-500 mt-2"><span id="owner"></span> · Horizonte: <span id="horizon"></span> · <span id="generated"></span></p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="card" id="ctx-card" style="display:none;">
<h2 class="text-sm font-bold uppercase text-slate-500 mb-2">Contexto de negócio</h2>
<p id="ctx"></p>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Prioridades estratégicas</h2>
<div id="priorities"></div>
</div>

<div class="grid sm:grid-cols-2 gap-6">
<div class="card" id="risks-card" style="display:none;">
<h2 class="text-lg font-bold mb-3">Riscos</h2>
<ul id="risks"></ul>
</div>
<div class="card" id="deps-card" style="display:none;">
<h2 class="text-lg font-bold mb-3">Dependências</h2>
<ul id="deps"></ul>
</div>
</div>

<div class="card" id="roadmap-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Roadmap trimestral</h2>
<div class="rail" id="roadmap"></div>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=people-strategy-okr-builder" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });
document.getElementById('title').textContent = DATA.title;
document.getElementById('owner').textContent = DATA.owner || '—';
document.getElementById('horizon').textContent = DATA.horizon || 'Anual';

if (DATA.business_context) {
  document.getElementById('ctx-card').style.display = '';
  document.getElementById('ctx').textContent = DATA.business_context;
}

document.getElementById('priorities').innerHTML = DATA.priorities.map((p, i) => {
  const krs = (p.key_results || []).map(k => {
    if (typeof k === 'string') return `<div class="kr"><span>${esc(k)}</span></div>`;
    const tgt = k.target ? `<span class="kr-target">${esc(k.target)}</span>` : '';
    return `<div class="kr"><span>${esc(k.kr || '')}${k.metric ? ` <span class="text-slate-400 text-xs">(${esc(k.metric)})</span>` : ''}</span>${tgt}</div>`;
  }).join('');
  const inits = (p.initiatives || []).length
    ? `<div class="mt-2 text-sm"><strong>Iniciativas:</strong><ul>${p.initiatives.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>` : '';
  return `<div class="priority">
    <div class="flex justify-between items-start gap-3 mb-1">
      <div class="font-bold text-slate-800 text-lg">${i + 1}. ${esc(p.name || '')}</div>
      ${p.owner ? `<span class="text-xs text-slate-500 whitespace-nowrap">Owner: <strong>${esc(p.owner)}</strong></span>` : ''}
    </div>
    ${p.business_goal ? `<div class="mb-2"><span class="badge">Negócio</span> <span class="text-sm text-slate-600">${esc(p.business_goal)}</span></div>` : ''}
    ${p.objective ? `<div class="text-sm mb-2"><strong>Objetivo:</strong> ${esc(p.objective)}</div>` : ''}
    <div class="text-xs uppercase font-bold text-slate-400 mt-2 mb-1">Key Results</div>
    ${krs}
    ${inits}
    ${p.metric ? `<div class="mt-2 text-xs text-slate-500">Métrica-chave: <strong>${esc(p.metric)}</strong></div>` : ''}
  </div>`;
}).join('');

if (DATA.risks.length) { document.getElementById('risks-card').style.display = ''; document.getElementById('risks').innerHTML = DATA.risks.map(r => `<li>${esc(r)}</li>`).join(''); }
if (DATA.dependencies.length) { document.getElementById('deps-card').style.display = ''; document.getElementById('deps').innerHTML = DATA.dependencies.map(r => `<li>${esc(r)}</li>`).join(''); }

if (DATA.roadmap.length) {
  document.getElementById('roadmap-card').style.display = '';
  document.getElementById('roadmap').innerHTML = DATA.roadmap.map(q =>
    `<div class="q"><div class="q-name">${esc(q.quarter || '')}</div><ul class="text-sm">${(q.milestones || []).map(m => `<li>${esc(m)}</li>`).join('')}</ul></div>`).join('');
}
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Renderiza one-pager HTML de estratégia de People + OKRs.")
    p.add_argument("--input", type=Path, help="JSON de estratégia (senão, lê do stdin)")
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
            sys.exit("Forneça --input <file> ou pipe o JSON de estratégia via stdin.")
        raw = json.loads(sys.stdin.read())

    data = normalize(raw)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = args.output or Path.cwd() / f"people-strategy-{_slug(data['title'])}-{ts}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    print(f"  {len(data['priorities'])} prioridade(s) estratégica(s)")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=people-strategy-okr-builder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
