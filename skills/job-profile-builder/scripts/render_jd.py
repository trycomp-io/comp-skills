#!/usr/bin/env python3
"""
render_jd.py — Renderiza Job Profile completo (JD + Scorecard + Roteiro de
Entrevistas) a partir de um JSON estruturado.

O JSON tipicamente é gerado pelo Claude após entrevista estruturada com o
hiring manager (10-15 perguntas cobrindo contexto, escopo, entregáveis,
red flags, comportamentos esperados).

Schema do JSON:
{
  "role_name": "Engineering Manager",
  "level": "L5",
  "area": "Engineering",
  "company": "Acme",
  "manager": "Maria Silva (VP Eng)",
  "summary": {
    "why_now": "...",
    "key_outcomes_6_months": ["...", "..."],
    "deal_breakers": ["...", "..."]
  },
  "jd": {
    "about_role": "...",
    "responsibilities": ["...", "..."],
    "requirements": ["...", "..."],
    "nice_to_have": ["...", "..."],
    "what_we_offer": ["...", "..."]
  },
  "scorecard": [
    {"criterion": "Liderança técnica", "weight": 5, "rubric": "5=...; 3=...; 1=..."},
    ...
  ],
  "interview_questions": [
    {"stage": "Recruiter screen", "question": "...", "what_to_look_for": "..."},
    {"stage": "Hiring manager", "question": "...", "what_to_look_for": "..."},
    ...
  ]
}

Uso:
    cat profile.json | python3 render_jd.py
    python3 render_jd.py --input profile.json
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

SKILL_NAME = "job-profile-builder"
SKILL_VERSION = "1.0.0"


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip()).strip("-").lower()[:50] or "jd"


def _esc(s: Any) -> str:
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>Job Profile — {role}</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  body{{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b}}
  .card{{background:white;border-radius:12px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin-bottom:1.5rem}}
  h1{{font-size:2.25rem;font-weight:800;color:#0f172a}}
  h2{{font-size:1.5rem;font-weight:700;color:#0f172a;margin-bottom:1rem;border-bottom:2px solid #f1f5f9;padding-bottom:.5rem}}
  h3{{font-size:1.1rem;font-weight:600;color:#0f172a;margin-top:1rem;margin-bottom:.5rem}}
  ul{{list-style:disc;padding-left:1.5rem}}
  li{{padding:.3rem 0}}
  .scorecard-row{{display:grid;grid-template-columns:1fr 80px;gap:1rem;padding:1rem;border-bottom:1px solid #e2e8f0;align-items:center}}
  .weight{{display:inline-block;background:#fee2e2;color:#991b1b;padding:.2rem .6rem;border-radius:999px;font-size:.75rem;font-weight:600;text-align:center}}
  .stage{{display:inline-block;background:#dbeafe;color:#1e40af;padding:.2rem .6rem;border-radius:999px;font-size:.7rem;font-weight:600;margin-bottom:.25rem}}
  pre{{background:#f1f5f9;padding:.75rem;border-radius:6px;white-space:pre-wrap;font-family:inherit;font-size:.875rem;color:#475569}}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-4xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Job Profile</div>
<h1>{role}</h1>
<p class="text-slate-600 mt-2">{meta}</p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

{body}

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=job-profile-builder" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div></body></html>
"""


def render_html(data: dict) -> str:
    role = _esc(data.get("role_name", "Posição"))
    meta = " · ".join(filter(None, [
        f"Nível {_esc(data.get('level'))}" if data.get("level") else "",
        _esc(data.get("area")),
        _esc(data.get("company")),
        f"Hiring manager: {_esc(data.get('manager'))}" if data.get("manager") else "",
    ]))

    parts = []
    summary = data.get("summary") or {}
    if summary:
        parts.append('<div class="card"><h2>Resumo executivo</h2>')
        if summary.get("why_now"):
            parts.append(f'<h3>Por que essa vaga agora?</h3><p>{_esc(summary["why_now"])}</p>')
        if summary.get("key_outcomes_6_months"):
            parts.append("<h3>Outcomes esperados nos primeiros 6 meses</h3><ul>")
            for o in summary["key_outcomes_6_months"]:
                parts.append(f"<li>{_esc(o)}</li>")
            parts.append("</ul>")
        if summary.get("deal_breakers"):
            parts.append("<h3>Deal-breakers</h3><ul>")
            for d in summary["deal_breakers"]:
                parts.append(f"<li>{_esc(d)}</li>")
            parts.append("</ul>")
        parts.append("</div>")

    jd = data.get("jd") or {}
    if jd:
        parts.append('<div class="card"><h2>Job Description</h2>')
        if jd.get("about_role"):
            parts.append(f'<h3>Sobre a vaga</h3><p>{_esc(jd["about_role"])}</p>')
        for label, key in [("Responsabilidades", "responsibilities"),
                            ("Requisitos", "requirements"),
                            ("Diferenciais (nice to have)", "nice_to_have"),
                            ("O que oferecemos", "what_we_offer")]:
            items = jd.get(key) or []
            if items:
                parts.append(f"<h3>{label}</h3><ul>")
                for it in items:
                    parts.append(f"<li>{_esc(it)}</li>")
                parts.append("</ul>")
        parts.append("</div>")

    scorecard = data.get("scorecard") or []
    if scorecard:
        parts.append('<div class="card"><h2>Scorecard de avaliação</h2>')
        parts.append('<p class="text-sm text-slate-600 mb-4">Cada entrevistador pontua cada critério de 1-5. Soma ponderada pelo peso.</p>')
        for s in scorecard:
            parts.append(f'<div class="scorecard-row">')
            parts.append(f'<div><strong>{_esc(s.get("criterion"))}</strong>')
            if s.get("rubric"):
                parts.append(f'<div class="text-xs text-slate-500 mt-1">{_esc(s["rubric"])}</div>')
            parts.append('</div>')
            parts.append(f'<div class="weight">Peso {_esc(s.get("weight", "—"))}</div>')
            parts.append('</div>')
        parts.append("</div>")

    questions = data.get("interview_questions") or []
    if questions:
        parts.append('<div class="card"><h2>Roteiro de entrevistas</h2>')
        for q in questions:
            parts.append('<div class="mb-4">')
            if q.get("stage"):
                parts.append(f'<div class="stage">{_esc(q["stage"])}</div>')
            parts.append(f'<div class="font-medium">{_esc(q.get("question"))}</div>')
            if q.get("what_to_look_for"):
                parts.append(f'<div class="text-sm text-slate-600 mt-1"><strong>O que procurar:</strong> {_esc(q["what_to_look_for"])}</div>')
            parts.append("</div>")
        parts.append("</div>")

    return HTML_TEMPLATE.format(role=role, meta=meta or "Job profile estruturado", body="\n".join(parts))


def render_md(data: dict) -> str:
    lines = []
    lines.append(f"# Job Profile — {data.get('role_name', 'Posição')}\n")
    meta = []
    for k, label in [("level", "Nível"), ("area", "Área"), ("company", "Empresa"), ("manager", "Hiring Manager")]:
        if data.get(k):
            meta.append(f"**{label}:** {data[k]}")
    if meta:
        lines.append("  \n".join(meta) + "\n")

    summary = data.get("summary") or {}
    if summary:
        lines.append("\n## Resumo executivo\n")
        if summary.get("why_now"):
            lines.append(f"**Por que agora:** {summary['why_now']}\n")
        if summary.get("key_outcomes_6_months"):
            lines.append("\n**Outcomes em 6 meses:**\n")
            for o in summary["key_outcomes_6_months"]:
                lines.append(f"- {o}")
        if summary.get("deal_breakers"):
            lines.append("\n**Deal-breakers:**\n")
            for d in summary["deal_breakers"]:
                lines.append(f"- {d}")

    jd = data.get("jd") or {}
    if jd:
        lines.append("\n## Job Description\n")
        if jd.get("about_role"):
            lines.append(f"{jd['about_role']}\n")
        for label, key in [("Responsabilidades", "responsibilities"),
                            ("Requisitos", "requirements"),
                            ("Diferenciais", "nice_to_have"),
                            ("O que oferecemos", "what_we_offer")]:
            items = jd.get(key) or []
            if items:
                lines.append(f"\n### {label}\n")
                for it in items:
                    lines.append(f"- {it}")

    scorecard = data.get("scorecard") or []
    if scorecard:
        lines.append("\n## Scorecard\n")
        lines.append("| Critério | Peso | Rubrica |\n|---|---|---|\n")
        for s in scorecard:
            rubric = (s.get("rubric") or "").replace("\n", " ").replace("|", "\\|")
            lines.append(f"| {s.get('criterion', '')} | {s.get('weight', '')} | {rubric} |")

    questions = data.get("interview_questions") or []
    if questions:
        lines.append("\n## Roteiro de entrevistas\n")
        for q in questions:
            stage = f"**{q.get('stage')}** — " if q.get("stage") else ""
            lines.append(f"\n- {stage}{q.get('question', '')}")
            if q.get("what_to_look_for"):
                lines.append(f"  - *O que procurar:* {q['what_to_look_for']}")

    lines.append("\n---\n— Powered by Comp · https://comp.vc?utm_source=skill-output&utm_medium=md-footer&utm_campaign=eam&utm_content=job-profile-builder")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Renderiza Job Profile (HTML + MD) a partir de JSON.")
    p.add_argument("--input", type=Path, help="JSON com a estrutura do profile (default: stdin)")
    p.add_argument("--output", type=Path, help="Caminho do HTML de saída")
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
    slug = _slug(data.get("role_name", "jd"))
    out_html = args.output or (Path.cwd() / f"jd-{slug}-{ts}.html")
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

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=job-profile-builder")
    return 0


# Workaround for type annotation (Any)
from typing import Any  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
