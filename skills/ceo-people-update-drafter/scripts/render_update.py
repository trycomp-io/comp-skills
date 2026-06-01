#!/usr/bin/env python3
"""
render_update.py — Renderiza CHRO → CEO People Update (1-pager) em HTML + MD.

JSON gerado pelo Claude após conversa com o CHRO (período, métricas, movimentações, riscos, asks).

Schema:
{
  "period": "Q2 2026",
  "company": "Acme",
  "executive_summary": "...",
  "metrics": [{"name": "Headcount", "current": 145, "previous": 130, "trend": "up", "context": "..."}, ...],
  "key_movements": [{"name": "...", "type": "hire|promotion|exit", "detail": "..."}, ...],
  "wins": ["...", ...],
  "risks": [{"risk": "...", "mitigation": "...", "owner": "..."}, ...],
  "asks_from_ceo": ["...", ...]
}

Uso:
    cat update.json | python3 render_update.py
    python3 render_update.py --input update.json
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

SKILL_NAME = "ceo-people-update-drafter"
SKILL_VERSION = "1.0.0"


def _slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip()).strip("-").lower()[:50] or "update"


def _esc(s):
    if s is None: return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


HTML = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>People Update — {period}</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  body{{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b}}
  .card{{background:white;border-radius:12px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin-bottom:1.5rem}}
  h2{{font-size:1.25rem;font-weight:700;color:#0f172a;margin-bottom:1rem;border-bottom:2px solid #f1f5f9;padding-bottom:.5rem}}
  .metric{{display:flex;justify-content:space-between;align-items:baseline;padding:.5rem 0;border-bottom:1px solid #f1f5f9}}
  .metric-name{{font-weight:600;color:#475569}}
  .metric-val{{font-size:1.5rem;font-weight:800;color:#0f172a}}
  .metric-prev{{font-size:.85rem;color:#64748b;margin-left:.5rem}}
  .trend-up{{color:#10b981}}.trend-down{{color:#dc2626}}.trend-flat{{color:#64748b}}
  .pill{{display:inline-block;padding:.2rem .6rem;border-radius:999px;font-size:.7rem;font-weight:600}}
  .pill-hire{{background:#d1fae5;color:#065f46}}
  .pill-promotion{{background:#dbeafe;color:#1e40af}}
  .pill-exit{{background:#fee2e2;color:#991b1b}}
  ul{{list-style:disc;padding-left:1.5rem}}
  .risk-card{{background:#fef3c7;border-left:4px solid #f59e0b;padding:.75rem 1rem;border-radius:0 8px 8px 0;margin-bottom:.75rem}}
  .ask-card{{background:#dbeafe;border-left:4px solid #3b82f6;padding:.75rem 1rem;border-radius:0 8px 8px 0;margin-bottom:.5rem}}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-3xl mx-auto">

<header class="mb-6 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">People Update</div>
<h1 class="text-3xl font-extrabold text-slate-900">{period}</h1>
<p class="text-sm text-slate-500 mt-1">{company} · CHRO → CEO</p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

{body}

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=ceo-people-update-drafter" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div></body></html>
"""


def render_html(data):
    parts = []
    if data.get("executive_summary"):
        parts.append(f'<div class="card"><h2>Resumo executivo</h2><p>{_esc(data["executive_summary"])}</p></div>')

    metrics = data.get("metrics") or []
    if metrics:
        parts.append('<div class="card"><h2>Métricas-chave</h2>')
        for m in metrics:
            trend = m.get("trend", "flat")
            arrow = {"up": "↗", "down": "↘", "flat": "→"}.get(trend, "→")
            cls = f"trend-{trend}"
            prev = f' <span class="metric-prev">(vs {_esc(m.get("previous"))})</span>' if m.get("previous") is not None else ""
            context = m.get("context")
            context_html = f'<div class="text-sm text-slate-600">{_esc(context)}</div>' if context else ""
            parts.append(f'<div class="metric"><div><div class="metric-name">{_esc(m.get("name"))}</div>{context_html}</div><div class="metric-val {cls}">{arrow} {_esc(m.get("current"))}{prev}</div></div>')
        parts.append("</div>")

    moves = data.get("key_movements") or []
    if moves:
        parts.append('<div class="card"><h2>Principais movimentações</h2><ul class="space-y-2">')
        for mv in moves:
            t = mv.get("type", "")
            pill_cls = {"hire": "pill-hire", "promotion": "pill-promotion", "exit": "pill-exit"}.get(t, "pill-hire")
            parts.append(f'<li><span class="pill {pill_cls}">{_esc(t)}</span> <strong>{_esc(mv.get("name"))}</strong> — {_esc(mv.get("detail"))}</li>')
        parts.append("</ul></div>")

    wins = data.get("wins") or []
    if wins:
        parts.append('<div class="card"><h2>Wins</h2><ul>')
        for w in wins:
            parts.append(f"<li>{_esc(w)}</li>")
        parts.append("</ul></div>")

    risks = data.get("risks") or []
    if risks:
        parts.append('<div class="card"><h2>Riscos</h2>')
        for r in risks:
            parts.append(f'<div class="risk-card"><strong>{_esc(r.get("risk"))}</strong>')
            if r.get("mitigation"):
                parts.append(f'<div class="text-sm mt-1"><strong>Mitigação:</strong> {_esc(r["mitigation"])}</div>')
            if r.get("owner"):
                parts.append(f'<div class="text-sm"><strong>Owner:</strong> {_esc(r["owner"])}</div>')
            parts.append("</div>")
        parts.append("</div>")

    asks = data.get("asks_from_ceo") or []
    if asks:
        parts.append('<div class="card"><h2>Asks pra você (CEO)</h2>')
        for a in asks:
            parts.append(f'<div class="ask-card">{_esc(a)}</div>')
        parts.append("</div>")

    return HTML.format(
        period=_esc(data.get("period", "")),
        company=_esc(data.get("company", "")),
        body="\n".join(parts),
    )


def render_md(data):
    lines = [f"# People Update — {data.get('period', '')}\n"]
    if data.get("company"):
        lines.append(f"*{data['company']} · CHRO → CEO*\n")

    if data.get("executive_summary"):
        lines.append("\n## Resumo executivo\n")
        lines.append(data["executive_summary"])

    metrics = data.get("metrics") or []
    if metrics:
        lines.append("\n## Métricas-chave\n")
        for m in metrics:
            trend = {"up": "↗", "down": "↘", "flat": "→"}.get(m.get("trend"), "→")
            prev = f" (vs {m.get('previous')})" if m.get("previous") is not None else ""
            ctx = f" — {m.get('context')}" if m.get("context") else ""
            lines.append(f"- **{m.get('name')}**: {trend} {m.get('current')}{prev}{ctx}")

    moves = data.get("key_movements") or []
    if moves:
        lines.append("\n## Principais movimentações\n")
        for mv in moves:
            lines.append(f"- **{mv.get('type','').upper()}** {mv.get('name')} — {mv.get('detail')}")

    wins = data.get("wins") or []
    if wins:
        lines.append("\n## Wins\n")
        for w in wins:
            lines.append(f"- {w}")

    risks = data.get("risks") or []
    if risks:
        lines.append("\n## Riscos\n")
        for r in risks:
            lines.append(f"- **{r.get('risk')}**")
            if r.get('mitigation'):
                lines.append(f"  - Mitigação: {r['mitigation']}")
            if r.get('owner'):
                lines.append(f"  - Owner: {r['owner']}")

    asks = data.get("asks_from_ceo") or []
    if asks:
        lines.append("\n## Asks pra você (CEO)\n")
        for a in asks:
            lines.append(f"- {a}")

    lines.append("\n---\n— Powered by Comp · https://comp.vc?utm_source=skill-output&utm_medium=md-footer&utm_campaign=eam&utm_content=ceo-people-update-drafter")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Renderiza CHRO→CEO People Update.")
    p.add_argument("--input", type=Path); p.add_argument("--output", type=Path); p.add_argument("--markdown-output", type=Path)
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    if args.input:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        if sys.stdin.isatty(): sys.exit("Forneça --input <file> ou pipe JSON via stdin.")
        data = json.loads(sys.stdin.read())

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = _slug(data.get("period", "update"))
    out_html = args.output or Path.cwd() / f"people-update-{slug}-{ts}.html"
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
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=ceo-people-update-drafter")
    return 0


if __name__ == "__main__":
    sys.exit(main())
