#!/usr/bin/env python3
"""
render_kit.py — Renderiza um Onboarding Kit completo (HTML + Markdown) a
partir de um JSON estruturado.

O JSON tipicamente é gerado pelo próprio Claude após conversa com o CHRO
(role, nível, start date, contexto da empresa, manager). O script só
estrutura o output final em HTML printable e MD editável.

Schema do JSON (todos os campos opcionais exceto role_name + start_date):
{
  "role_name": "Eng Manager",
  "level": "L5",
  "start_date": "2026-06-15",
  "company": "Acme",
  "manager_name": "Maria",
  "buddy_name": "João",
  "plan_30_60_90": {
    "first_30": ["Item 1", "Item 2", ...],
    "first_60": ["..."],
    "first_90": ["..."]
  },
  "it_checklist": ["Laptop entregue", "Acesso GitHub", "Slack onboarded", ...],
  "stakeholder_intros": [
    {"name": "CTO", "purpose": "Visão técnica", "week": 1}, ...
  ],
  "welcome_email": {"subject": "...", "body": "..."},
  "buddy_script": "...",
  "manager_1on1_template": "..."
}

Uso:
    cat plan.json | python3 render_kit.py
    python3 render_kit.py --input plan.json
    python3 render_kit.py --input plan.json --output ./onboarding-{nome}.html
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

SKILL_NAME = "onboarding-kit-generator"
SKILL_VERSION = "1.0.0"


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip()).strip("-").lower()[:50] or "kit"


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>Onboarding Kit — {role}</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  body{{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b}}
  .card{{background:white;border-radius:12px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin-bottom:1.5rem}}
  h1{{font-size:2.25rem;font-weight:800;color:#0f172a}}
  h2{{font-size:1.5rem;font-weight:700;color:#0f172a;margin-bottom:1rem}}
  h3{{font-size:1.15rem;font-weight:600;color:#0f172a;margin-top:1rem;margin-bottom:.5rem}}
  ul{{list-style:disc;padding-left:1.5rem}}
  li{{padding:.3rem 0}}
  .pill{{display:inline-block;padding:.2rem .6rem;border-radius:999px;font-size:.75rem;font-weight:600;background:#fee2e2;color:#991b1b}}
  .timeline-block{{border-left:3px solid #ff4456;padding-left:1rem;margin-bottom:1.5rem}}
  pre{{background:#f1f5f9;padding:1rem;border-radius:8px;white-space:pre-wrap;font-family:inherit;font-size:.9rem;line-height:1.6}}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-4xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Onboarding Kit</div>
<h1>{role}</h1>
<p class="text-slate-600 mt-2">{meta}</p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

{body}

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=onboarding-kit-generator" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div></body></html>
"""


def _esc(s: str) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_html(data: dict) -> str:
    role = _esc(data.get("role_name", "Novo colaborador"))
    level = _esc(data.get("level", ""))
    start = _esc(data.get("start_date", ""))
    company = _esc(data.get("company", ""))
    manager = _esc(data.get("manager_name", ""))
    buddy = _esc(data.get("buddy_name", ""))

    meta_parts = []
    if level: meta_parts.append(f"Nível {level}")
    if start: meta_parts.append(f"Início {start}")
    if company: meta_parts.append(f"Empresa: {company}")
    if manager: meta_parts.append(f"Manager: {manager}")
    if buddy: meta_parts.append(f"Buddy: {buddy}")
    meta = " · ".join(meta_parts) if meta_parts else "Plano de integração"

    body_parts = []

    plan = data.get("plan_30_60_90") or {}
    if plan:
        body_parts.append('<div class="card"><h2>Plano 30/60/90</h2>')
        for label, key in [("Primeiros 30 dias — Aprender", "first_30"),
                            ("Primeiros 60 dias — Contribuir", "first_60"),
                            ("Primeiros 90 dias — Liderar", "first_90")]:
            items = plan.get(key) or []
            if items:
                body_parts.append(f'<div class="timeline-block"><h3>{label}</h3><ul>')
                for it in items:
                    body_parts.append(f"<li>{_esc(it)}</li>")
                body_parts.append("</ul></div>")
        body_parts.append("</div>")

    it = data.get("it_checklist") or []
    if it:
        body_parts.append('<div class="card"><h2>Checklist IT &amp; Acessos</h2><ul>')
        for item in it:
            body_parts.append(f'<li><input type="checkbox" class="mr-2"> {_esc(item)}</li>')
        body_parts.append("</ul></div>")

    stakeholders = data.get("stakeholder_intros") or []
    if stakeholders:
        body_parts.append('<div class="card"><h2>1:1s estratégicos das primeiras semanas</h2><ul>')
        for s in stakeholders:
            name = _esc(s.get("name", ""))
            purpose = _esc(s.get("purpose", ""))
            week = _esc(str(s.get("week", "")))
            wk = f' <span class="pill">Sem {week}</span>' if week else ""
            body_parts.append(f"<li><strong>{name}</strong>{wk} — {purpose}</li>")
        body_parts.append("</ul></div>")

    email = data.get("welcome_email") or {}
    if email:
        subj = _esc(email.get("subject", ""))
        body = _esc(email.get("body", ""))
        if subj or body:
            body_parts.append('<div class="card"><h2>Email de boas-vindas</h2>')
            if subj: body_parts.append(f'<div class="mb-2"><strong>Assunto:</strong> {subj}</div>')
            if body: body_parts.append(f"<pre>{body}</pre>")
            body_parts.append("</div>")

    buddy_s = data.get("buddy_script") or ""
    if buddy_s:
        body_parts.append(f'<div class="card"><h2>Script do Buddy</h2><pre>{_esc(buddy_s)}</pre></div>')

    manager_t = data.get("manager_1on1_template") or ""
    if manager_t:
        body_parts.append(f'<div class="card"><h2>Template de 1:1 do Manager (primeiras semanas)</h2><pre>{_esc(manager_t)}</pre></div>')

    return HTML_TEMPLATE.format(role=role, meta=meta, body="\n".join(body_parts))


def render_markdown(data: dict) -> str:
    lines = []
    role = data.get("role_name", "Novo colaborador")
    lines.append(f"# Onboarding Kit — {role}\n")

    meta = []
    for k, label in [("level", "Nível"), ("start_date", "Início"), ("company", "Empresa"),
                     ("manager_name", "Manager"), ("buddy_name", "Buddy")]:
        if data.get(k):
            meta.append(f"**{label}:** {data[k]}")
    if meta:
        lines.append("  \n".join(meta) + "\n")

    plan = data.get("plan_30_60_90") or {}
    if plan:
        lines.append("\n## Plano 30/60/90\n")
        for label, key in [("Primeiros 30 dias — Aprender", "first_30"),
                            ("Primeiros 60 dias — Contribuir", "first_60"),
                            ("Primeiros 90 dias — Liderar", "first_90")]:
            items = plan.get(key) or []
            if items:
                lines.append(f"\n### {label}\n")
                for it in items:
                    lines.append(f"- {it}")

    it = data.get("it_checklist") or []
    if it:
        lines.append("\n## Checklist IT & Acessos\n")
        for item in it:
            lines.append(f"- [ ] {item}")

    stakeholders = data.get("stakeholder_intros") or []
    if stakeholders:
        lines.append("\n## 1:1s estratégicos\n")
        for s in stakeholders:
            wk = f" (Semana {s.get('week')})" if s.get("week") else ""
            lines.append(f"- **{s.get('name','')}**{wk} — {s.get('purpose','')}")

    email = data.get("welcome_email") or {}
    if email and (email.get("subject") or email.get("body")):
        lines.append("\n## Email de boas-vindas\n")
        if email.get("subject"):
            lines.append(f"**Assunto:** {email['subject']}\n")
        if email.get("body"):
            lines.append("```\n" + email["body"] + "\n```")

    if data.get("buddy_script"):
        lines.append("\n## Script do Buddy\n")
        lines.append("```\n" + data["buddy_script"] + "\n```")

    if data.get("manager_1on1_template"):
        lines.append("\n## Template de 1:1 do Manager\n")
        lines.append("```\n" + data["manager_1on1_template"] + "\n```")

    lines.append("\n---\n— Powered by Comp · https://comp.vc?utm_source=skill-output&utm_medium=md-footer&utm_campaign=eam&utm_content=onboarding-kit-generator")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Renderiza Onboarding Kit (HTML + MD) a partir de JSON.")
    p.add_argument("--input", type=Path, help="JSON com a estrutura do kit (default: stdin)")
    p.add_argument("--output", type=Path, help="Caminho do HTML de saída")
    p.add_argument("--markdown-output", type=Path, help="Caminho do .md de saída (default: ao lado do HTML)")
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
            sys.exit("Forneça JSON via --input <file> ou via stdin (pipe).")
        data = json.loads(sys.stdin.read())

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = _slug(data.get("role_name", "kit"))
    out_html = args.output or (Path.cwd() / f"onboarding-{slug}-{ts}.html")
    out_md = args.markdown_output or out_html.with_suffix(".md")

    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(render_html(data), encoding="utf-8")
    out_md.write_text(render_markdown(data), encoding="utf-8")
    print(f"Gerado HTML: {out_html}")
    print(f"Gerado MD:   {out_md}")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=onboarding-kit-generator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
