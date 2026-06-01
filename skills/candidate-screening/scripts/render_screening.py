#!/usr/bin/env python3
"""
render_screening.py — Renderiza um relatório HTML ranqueado de candidatos
contra os critérios de uma vaga (scorecard).

JSON tipicamente gerado pelo Claude após avaliar cada candidato contra os
critérios do job profile (scorecard do skill job-profile-builder ou rubrica
informada pelo CHRO).

Schema do JSON:
{
  "role_name": "Engineering Manager",
  "company": "Acme",
  "n_candidates": 12,
  "criteria": [
    {"name": "Liderança técnica", "weight": 5},
    {"name": "People management", "weight": 4}, ...
  ],
  "candidates": [
    {
      "name": "Ana Souza",
      "current_role": "EM @ Outra Empresa",
      "scores": [
        {"criterion": "Liderança técnica", "score": 4, "justification": "Liderou squad de 6 SWEs em rebuild de plataforma..."},
        ...
      ],
      "overall_score": 4.2,
      "flags": ["Plus: open source contributions notórias", "Atenção: 3 trocas em 4 anos"],
      "recommendation": "interview"
    }
  ]
}

Uso:
    cat candidates.json | python3 render_screening.py
    python3 render_screening.py --input candidates.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "candidate-screening"
SKILL_VERSION = "1.0.0"


REC_LABELS = {
    "interview":     ("Entrevistar", "bg-emerald-100 text-emerald-800"),
    "phone_screen":  ("Phone screen", "bg-blue-100 text-blue-800"),
    "decline":       ("Declinar", "bg-rose-100 text-rose-800"),
    "review":        ("Revisar", "bg-amber-100 text-amber-800"),
}


def _esc(s: Any) -> str:
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip()).strip("-").lower()[:50] or "screening"


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>Candidate Screening — {role}</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  body{{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b}}
  .card{{background:white;border-radius:12px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin-bottom:1.5rem}}
  table{{width:100%;border-collapse:collapse;font-size:.9rem}}
  th{{background:#1e293b;color:white;padding:.75rem;text-align:left;font-weight:600;font-size:.8rem;text-transform:uppercase;letter-spacing:.05em}}
  td{{padding:.85rem .75rem;border-bottom:1px solid #e2e8f0;vertical-align:top}}
  tr:hover{{background:#f8fafc}}
  .pill{{display:inline-block;padding:.25rem .65rem;border-radius:999px;font-size:.7rem;font-weight:600}}
  .score-bar{{height:6px;border-radius:3px;background:#e2e8f0;overflow:hidden;width:80px}}
  .score-fill{{height:100%;background:linear-gradient(90deg,#dc2626 0%,#f59e0b 33%,#65a30d 66%,#10b981 100%)}}
  .crit-card{{background:#f8fafc;border-radius:8px;padding:.75rem;margin-bottom:.5rem;font-size:.85rem}}
  .flag-positive{{color:#065f46;font-weight:500}}
  .flag-warning{{color:#92400e;font-weight:500}}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-6xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Candidate Screening</div>
<h1 class="text-3xl font-extrabold text-slate-900">{role}</h1>
<p class="text-slate-600 mt-2">{meta} · {n_cand} candidato(s) avaliado(s)</p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="card">
<h2 class="text-xl font-bold mb-4">Ranking</h2>
<div class="overflow-x-auto"><table>
<thead><tr><th>#</th><th>Candidato</th><th>Cargo atual</th><th>Score</th><th>Recomendação</th></tr></thead>
<tbody id="rank-tbody">{rank_rows}</tbody>
</table></div>
</div>

<div id="details">{detail_cards}</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=candidate-screening" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div></body></html>
"""


def render_html(data: dict) -> str:
    role = _esc(data.get("role_name", "Posição"))
    company = _esc(data.get("company", ""))
    meta = company if company else "Screening contra scorecard"

    candidates = sorted(
        data.get("candidates", []),
        key=lambda c: c.get("overall_score", 0),
        reverse=True,
    )
    n = len(candidates)

    rank_rows = []
    for i, c in enumerate(candidates, 1):
        score = c.get("overall_score", 0)
        pct = min(100, max(0, score / 5 * 100))
        rec_label, rec_class = REC_LABELS.get(c.get("recommendation", "review"), REC_LABELS["review"])
        rank_rows.append(
            f"<tr>"
            f"<td><strong>{i}</strong></td>"
            f"<td><strong>{_esc(c.get('name'))}</strong></td>"
            f"<td>{_esc(c.get('current_role', '—'))}</td>"
            f"<td><div class='flex items-center gap-2'><div class='score-bar'><div class='score-fill' style='width:{pct}%'></div></div><strong>{score:.1f}</strong></div></td>"
            f"<td><span class='pill {rec_class}'>{rec_label}</span></td>"
            f"</tr>"
        )

    detail_cards = []
    for c in candidates:
        rec_label, rec_class = REC_LABELS.get(c.get("recommendation", "review"), REC_LABELS["review"])
        flags_html = ""
        for f in c.get("flags", []):
            cls = "flag-positive" if str(f).strip().lower().startswith(("plus", "+")) else "flag-warning"
            flags_html += f"<li class='{cls}'>{_esc(f)}</li>"
        crits_html = ""
        for s in c.get("scores", []):
            crits_html += (
                f"<div class='crit-card'>"
                f"<div class='flex justify-between mb-1'>"
                f"<strong>{_esc(s.get('criterion'))}</strong>"
                f"<span class='font-bold text-rose-600'>{s.get('score', '—')}/5</span>"
                f"</div>"
                f"<div class='text-slate-600'>{_esc(s.get('justification', ''))}</div>"
                f"</div>"
            )
        detail_cards.append(
            f"<div class='card'>"
            f"<div class='flex justify-between items-start mb-2'>"
            f"<div><h3 class='text-lg font-bold'>{_esc(c.get('name'))}</h3>"
            f"<div class='text-sm text-slate-600'>{_esc(c.get('current_role', ''))}</div></div>"
            f"<div class='text-right'><div class='text-3xl font-extrabold text-slate-900'>{c.get('overall_score', 0):.1f}</div>"
            f"<span class='pill {rec_class}'>{rec_label}</span></div>"
            f"</div>"
            f"<h4 class='font-semibold mt-4 mb-2'>Critérios</h4>"
            f"{crits_html}"
            + (f"<h4 class='font-semibold mt-4 mb-2'>Flags</h4><ul class='list-disc pl-5'>{flags_html}</ul>" if flags_html else "")
            + "</div>"
        )

    return HTML_TEMPLATE.format(
        role=role, meta=meta, n_cand=n,
        rank_rows="\n".join(rank_rows),
        detail_cards="\n".join(detail_cards),
    )


def render_md(data: dict) -> str:
    lines = [f"# Candidate Screening — {data.get('role_name', '')}\n"]
    candidates = sorted(data.get("candidates", []), key=lambda c: c.get("overall_score", 0), reverse=True)
    lines.append(f"{len(candidates)} candidato(s) avaliado(s).\n\n## Ranking\n")
    lines.append("| # | Candidato | Cargo atual | Score | Recomendação |\n|---|---|---|---|---|")
    for i, c in enumerate(candidates, 1):
        rec_label, _ = REC_LABELS.get(c.get("recommendation", "review"), REC_LABELS["review"])
        lines.append(f"| {i} | **{c.get('name','')}** | {c.get('current_role','—')} | {c.get('overall_score',0):.1f} | {rec_label} |")
    lines.append("\n## Detalhes por candidato\n")
    for c in candidates:
        lines.append(f"\n### {c.get('name','')} — {c.get('overall_score', 0):.1f}")
        lines.append(f"*{c.get('current_role','')}* — **Recomendação:** {REC_LABELS.get(c.get('recommendation','review'), REC_LABELS['review'])[0]}\n")
        for s in c.get("scores", []):
            lines.append(f"- **{s.get('criterion','')}** ({s.get('score','—')}/5): {s.get('justification','')}")
        if c.get("flags"):
            lines.append("\n**Flags:**")
            for f in c.get("flags", []):
                lines.append(f"- {f}")
    lines.append("\n---\n— Powered by Comp · https://comp.vc?utm_source=skill-output&utm_medium=md-footer&utm_campaign=eam&utm_content=candidate-screening")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Renderiza screening de candidatos (HTML + MD) a partir de JSON.")
    p.add_argument("--input", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--markdown-output", type=Path)
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    if args.input:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        if sys.stdin.isatty():
            sys.exit("Forneça --input <file> ou pipe JSON via stdin.")
        data = json.loads(sys.stdin.read())

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = _slug(data.get("role_name", "screening"))
    out_html = args.output or (Path.cwd() / f"screening-{slug}-{ts}.html")
    out_md = args.markdown_output or out_html.with_suffix(".md")
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(render_html(data), encoding="utf-8")
    out_md.write_text(render_md(data), encoding="utf-8")
    print(f"Gerado HTML: {out_html}")
    print(f"Gerado MD:   {out_md}")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=candidate-screening")
    return 0


if __name__ == "__main__":
    sys.exit(main())
