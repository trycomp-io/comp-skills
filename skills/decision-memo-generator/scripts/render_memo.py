#!/usr/bin/env python3
"""
render_memo.py — Renderiza memo estruturado de decisão pra people topics.
Frame: problem, context, options (com trade-offs), recommendation, risks,
ask. Output HTML + MD.

Uso:
    cat memo.json | python3 render_memo.py
"""

from __future__ import annotations

import argparse, json, re, sys, unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "decision-memo-generator"
SKILL_VERSION = "1.0.0"


def _slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip()).strip("-").lower()[:50] or "memo"


def _esc(s):
    if s is None: return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


HTML = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>Decision Memo — {title}</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  body{{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b;line-height:1.6}}
  .memo{{max-width:780px;background:white;border-radius:12px;padding:3rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin:2rem auto}}
  h1{{font-size:2rem;font-weight:800;margin-bottom:.5rem;color:#0f172a}}
  h2{{font-size:1.25rem;font-weight:700;margin-top:2rem;margin-bottom:1rem;color:#0f172a;padding-bottom:.5rem;border-bottom:2px solid #f1f5f9}}
  .meta{{font-size:.875rem;color:#64748b;margin-bottom:2rem;border-left:3px solid #ff4456;padding-left:1rem}}
  .meta strong{{color:#0f172a}}
  .option{{border:1px solid #e2e8f0;border-radius:8px;padding:1.25rem;margin-bottom:1rem;background:#fafbfc}}
  .option-name{{font-size:1.05rem;font-weight:700;color:#0f172a;margin-bottom:.5rem}}
  .pros-cons{{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-top:.75rem}}
  .pros{{background:#d1fae5;padding:.75rem;border-radius:6px}}
  .cons{{background:#fee2e2;padding:.75rem;border-radius:6px}}
  .pros strong{{color:#065f46}}.cons strong{{color:#991b1b}}
  .recommendation{{background:linear-gradient(to right,#fef3c7,white);border-left:4px solid #f59e0b;padding:1.5rem;border-radius:0 8px 8px 0;margin:1rem 0}}
  .ask{{background:#dbeafe;border-left:4px solid #3b82f6;padding:1.25rem;border-radius:0 8px 8px 0;margin-top:1rem;font-weight:600}}
  ul{{list-style:disc;padding-left:1.5rem}}
</style></head>
<body>
<div class="memo">

<h1>{title}</h1>
<div class="meta">
<strong>Autor:</strong> {author}<br>
<strong>Para:</strong> {decision_maker}<br>
<strong>Data:</strong> {date}<br>
<strong>Decisão até:</strong> {decision_by}
</div>

<h2>Problema / Decisão a tomar</h2>
<p>{problem}</p>

<h2>Contexto</h2>
{context_html}

<h2>Opções consideradas</h2>
{options_html}

<h2>Recomendação</h2>
<div class="recommendation">
<strong>Recomendo:</strong> {recommended_option}<br>
<div style="margin-top:.5rem;">{recommendation_rationale}</div>
</div>

{risks_html}

<h2>Ask</h2>
<div class="ask">{ask}</div>

</div>

<footer style="text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;padding:1rem;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=decision-memo-generator" style="color:#ff4456;font-weight:600;text-decoration:none;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</body></html>
"""


def render_html(d):
    context = d.get("context") or []
    if isinstance(context, str):
        context_html = f"<p>{_esc(context)}</p>"
    else:
        context_html = "<ul>" + "".join(f"<li>{_esc(c)}</li>" for c in context) + "</ul>"

    options = d.get("options") or []
    opts_html = []
    for o in options:
        pros = "".join(f"<li>{_esc(p)}</li>" for p in (o.get("pros") or []))
        cons = "".join(f"<li>{_esc(c)}</li>" for c in (o.get("cons") or []))
        opts_html.append(
            f'<div class="option">'
            f'<div class="option-name">{_esc(o.get("name"))}</div>'
            f'<div>{_esc(o.get("description", ""))}</div>'
            f'<div class="pros-cons">'
            f'<div class="pros"><strong>Prós</strong><ul>{pros}</ul></div>'
            f'<div class="cons"><strong>Contras</strong><ul>{cons}</ul></div>'
            f'</div></div>'
        )

    risks = d.get("risks") or []
    risks_html = ""
    if risks:
        risks_html = "<h2>Riscos</h2><ul>" + "".join(f"<li>{_esc(r)}</li>" for r in risks) + "</ul>"

    return HTML.format(
        title=_esc(d.get("title", "Decision Memo")),
        author=_esc(d.get("author", "")),
        decision_maker=_esc(d.get("decision_maker", "")),
        date=_esc(d.get("date", datetime.now().strftime("%Y-%m-%d"))),
        decision_by=_esc(d.get("decision_by", "")),
        problem=_esc(d.get("problem", "")),
        context_html=context_html,
        options_html="\n".join(opts_html),
        recommended_option=_esc(d.get("recommended_option", "")),
        recommendation_rationale=_esc(d.get("recommendation_rationale", "")),
        risks_html=risks_html,
        ask=_esc(d.get("ask", "")),
    )


def render_md(d):
    lines = [f"# {d.get('title', 'Decision Memo')}\n"]
    lines.append(f"**Autor:** {d.get('author','')}  ")
    lines.append(f"**Para:** {d.get('decision_maker','')}  ")
    lines.append(f"**Data:** {d.get('date', datetime.now().strftime('%Y-%m-%d'))}  ")
    if d.get("decision_by"):
        lines.append(f"**Decisão até:** {d['decision_by']}\n")

    lines.append("\n## Problema / Decisão a tomar\n")
    lines.append(d.get("problem", ""))

    lines.append("\n## Contexto\n")
    ctx = d.get("context")
    if isinstance(ctx, list):
        for c in ctx: lines.append(f"- {c}")
    elif ctx:
        lines.append(ctx)

    lines.append("\n## Opções consideradas\n")
    for o in d.get("options", []):
        lines.append(f"\n### {o.get('name')}")
        if o.get('description'): lines.append(o['description'])
        lines.append("\n**Prós:**")
        for p in o.get("pros", []): lines.append(f"- {p}")
        lines.append("\n**Contras:**")
        for c in o.get("cons", []): lines.append(f"- {c}")

    lines.append("\n## Recomendação\n")
    lines.append(f"**Recomendo:** {d.get('recommended_option','')}\n")
    lines.append(d.get("recommendation_rationale", ""))

    if d.get("risks"):
        lines.append("\n## Riscos\n")
        for r in d["risks"]: lines.append(f"- {r}")

    lines.append("\n## Ask\n")
    lines.append(d.get("ask", ""))

    lines.append("\n---\n— Powered by Comp · https://comp.vc?utm_source=skill-output&utm_medium=md-footer&utm_campaign=eam&utm_content=decision-memo-generator")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Renderiza decision memo (HTML + MD).")
    p.add_argument("--input", type=Path); p.add_argument("--output", type=Path); p.add_argument("--markdown-output", type=Path)
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    if args.input:
        d = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        if sys.stdin.isatty(): sys.exit("Forneça --input <file> ou pipe JSON via stdin.")
        d = json.loads(sys.stdin.read())

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = _slug(d.get("title", "memo"))
    out_html = args.output or Path.cwd() / f"memo-{slug}-{ts}.html"
    out_md = args.markdown_output or out_html.with_suffix(".md")
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(render_html(d), encoding="utf-8")
    out_md.write_text(render_md(d), encoding="utf-8")
    print(f"Gerado HTML: {out_html}\nGerado MD:   {out_md}")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=decision-memo-generator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
