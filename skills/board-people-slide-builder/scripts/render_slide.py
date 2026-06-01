#!/usr/bin/env python3
"""
render_slide.py — Renderiza o slide de People pra board meeting em HTML
formato 16:9 (1920x1080 friendly), pronto pra projetar ou exportar como
PNG/PDF.

JSON gerado pelo Claude após conversa com CHRO. Estruturado em:
- Período (Q + ano)
- 4 KPIs principais (number + trend + label)
- 3 highlights narrativos
- 1-2 risk/ask

Uso:
    cat slide.json | python3 render_slide.py
    python3 render_slide.py --input slide.json
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

SKILL_NAME = "board-people-slide-builder"
SKILL_VERSION = "1.0.0"


def _slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip()).strip("-").lower()[:50] or "slide"


def _esc(s):
    if s is None: return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


HTML = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>Board People Slide — {period}</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
  body{{font-family:'Inter',sans-serif;background:#f1f5f9;color:#0f172a;margin:0;padding:2rem;min-height:100vh;display:flex;align-items:center;justify-content:center}}
  .slide{{width:1920px;max-width:96vw;aspect-ratio:16/9;background:white;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,0.15);padding:5rem;display:flex;flex-direction:column;transform-origin:top center}}
  @media (max-width:1280px){{.slide{{transform:scale(0.66);margin:-15vh 0}}}}
  .eyebrow{{font-size:1rem;font-weight:700;color:#ff4456;letter-spacing:.1em;text-transform:uppercase}}
  h1{{font-size:3rem;font-weight:900;color:#0f172a;line-height:1.1;margin:0.5rem 0 0;letter-spacing:-.02em}}
  .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:2rem;margin:3rem 0}}
  .kpi{{padding:1.5rem;background:#f8fafc;border-radius:12px;border-left:6px solid #ff4456}}
  .kpi-val{{font-size:2.75rem;font-weight:900;color:#0f172a;line-height:1}}
  .kpi-trend{{font-size:1rem;font-weight:600;margin-left:.5rem}}
  .trend-up{{color:#059669}}.trend-down{{color:#dc2626}}.trend-flat{{color:#64748b}}
  .kpi-label{{font-size:.95rem;color:#475569;text-transform:uppercase;letter-spacing:.05em;font-weight:600;margin-top:.5rem}}
  .kpi-context{{font-size:.875rem;color:#64748b;margin-top:.4rem}}
  .lower{{display:grid;grid-template-columns:2fr 1fr;gap:2.5rem;flex:1}}
  .lower h3{{font-size:1.25rem;font-weight:700;color:#0f172a;margin-bottom:.75rem}}
  .highlight{{padding:.65rem 0;font-size:1.05rem;line-height:1.4;color:#1e293b;border-bottom:1px solid #e2e8f0}}
  .highlight:last-child{{border-bottom:none}}
  .ask{{background:#fef3c7;border-left:4px solid #f59e0b;padding:1rem;border-radius:0 8px 8px 0;margin-bottom:.75rem;font-size:.95rem}}
  .footer{{display:flex;justify-content:space-between;align-items:flex-end;margin-top:auto;padding-top:1.5rem;border-top:1px solid #e2e8f0;font-size:.75rem;color:#94a3b8}}
</style></head>
<body>
<div class="slide">

<header>
<div class="eyebrow">{eyebrow}</div>
<h1>{title}</h1>
</header>

<div class="kpis">
{kpis_html}
</div>

<div class="lower">
<div>
<h3>Highlights</h3>
{highlights_html}
</div>
<div>
{risks_asks_html}
</div>
</div>

<div class="footer">
<div>{company} · People & Culture · {period}</div>
<div>Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=board-people-slide-builder" style="color:#ff4456;font-weight:600;text-decoration:none;">Comp</a></div>
</div>

</div></body></html>
"""


def render_html(data):
    period = _esc(data.get("period", ""))
    company = _esc(data.get("company", ""))
    title = _esc(data.get("title", "People & Culture Update"))
    eyebrow = _esc(data.get("eyebrow", "Board Update"))

    kpis = data.get("kpis", [])[:4]  # max 4
    kpis_html = []
    for k in kpis:
        trend = k.get("trend", "flat")
        arrow = {"up": "↗", "down": "↘", "flat": "→"}.get(trend, "→")
        context = k.get("context")
        context_html = f'<div class="kpi-context">{_esc(context)}</div>' if context else ""
        kpis_html.append(
            f'<div class="kpi">'
            f'<div><span class="kpi-val">{_esc(k.get("value"))}</span><span class="kpi-trend trend-{trend}">{arrow}</span></div>'
            f'<div class="kpi-label">{_esc(k.get("label"))}</div>'
            f'{context_html}'
            f'</div>'
        )

    highlights = data.get("highlights", [])
    highlights_html = "".join(f'<div class="highlight">● {_esc(h)}</div>' for h in highlights)

    risks_html = []
    for r in data.get("risks", []):
        risks_html.append(f'<div class="ask"><strong>⚠ Risco:</strong> {_esc(r)}</div>')
    for a in data.get("asks", []):
        risks_html.append(f'<div class="ask"><strong>📌 Ask:</strong> {_esc(a)}</div>')
    risks_asks_html = "<h3>Riscos &amp; Asks</h3>" + "".join(risks_html) if risks_html else ""

    return HTML.format(
        period=period, company=company, title=title, eyebrow=eyebrow,
        kpis_html="\n".join(kpis_html),
        highlights_html=highlights_html or '<div class="highlight">—</div>',
        risks_asks_html=risks_asks_html,
    )


def main():
    p = argparse.ArgumentParser(description="Renderiza slide de People pro board.")
    p.add_argument("--input", type=Path); p.add_argument("--output", type=Path)
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
    slug = _slug(data.get("period", "slide"))
    out = args.output or Path.cwd() / f"board-people-slide-{slug}-{ts}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(data), encoding="utf-8")
    print(f"Gerado: {out}")
    print("Abra no browser e printe pra PDF (16:9) — pronto pra board deck.")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=board-people-slide-builder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
