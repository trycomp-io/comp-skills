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
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Job profile · {role} · Zivo</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Marcellus&family=Source+Sans+3:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<style>
:root {{
  --zivo-ink: #1A1A1A;
  --zivo-off-white: #F1F1EA;
  --zivo-white: #FFFFFF;
  --zivo-red: #F4364C;
  --zivo-red-hover: #E02A40;
  --zivo-red-pressed: #9E1528;
  --zivo-ink-80: rgba(26,26,26,.8);
  --zivo-ink-60: rgba(26,26,26,.6);
  --zivo-ink-40: rgba(26,26,26,.4);
  --zivo-ink-30: rgba(26,26,26,.3);
  --zivo-ink-20: rgba(26,26,26,.2);
  --zivo-ink-10: rgba(26,26,26,.1);
  --zivo-ink-05: rgba(26,26,26,.05);
  --zivo-success: #0B7A43; --zivo-success-bg: #DDF7EA; --zivo-success-fill: #12B76A;
  --zivo-warning: #985704; --zivo-warning-bg: #FFF2DA; --zivo-warning-fill: #F69B10;
  --zivo-error: #B3172A;   --zivo-error-bg: #FEE7EA;   --zivo-error-fill: #D61F35;
  --zivo-info: #0B58BB;    --zivo-info-bg: #E7F1FF;    --zivo-info-fill: #1C7CE5;
  --zivo-font-flare: "ABC Arizona Flare", Marcellus, Georgia, serif;
  --zivo-font-sans: "ABC Arizona Sans", "Source Sans 3", system-ui, -apple-system, "Segoe UI", sans-serif;
  --zivo-radius: 0;
  --gap: 24px;
}}

* {{ box-sizing: border-box; border-radius: 0; box-shadow: none; }}

body {{
  margin: 0;
  font-family: var(--zivo-font-sans);
  font-size: 16px;
  line-height: 1.5;
  color: var(--zivo-ink);
  background: var(--zivo-off-white);
  -webkit-font-smoothing: antialiased;
}}

h1, h2, h3, h4 {{
  font-family: var(--zivo-font-flare);
  font-weight: 400;
  font-style: normal;
  text-transform: none;
  margin: 0 0 .4em;
}}
h1 {{ font-size: 56px; line-height: 54px; letter-spacing: -0.02em; }}
h2 {{ font-size: 32px; line-height: 36px; letter-spacing: -0.01em; }}
h3 {{ font-size: 22px; line-height: 28px; }}
h4 {{ font-size: 18px; line-height: 24px; }}
p {{ margin: 0 0 1em; }}
small, .small {{ font-size: 14px; line-height: 20px; }}
.caption, .label {{
  font-size: 12px; line-height: 16px; text-transform: uppercase;
  letter-spacing: .04em; color: var(--zivo-ink-60);
}}
.muted {{ color: var(--zivo-ink-60); }}
a {{ color: var(--zivo-ink); text-decoration: underline; text-underline-offset: 2px; }}
a:hover {{ color: var(--zivo-ink-80); }}

/* Square node / overline marker */
.zv-dot {{ display: inline-block; width: 8px; height: 8px; background: currentColor; margin-right: 8px; vertical-align: 1px; }}
.zv-dot--red {{ background: var(--zivo-red); }}

/* Header row: four captions over a 1px rule */
.zv-header-row {{
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--gap);
  padding-bottom: 10px; margin-bottom: 40px;
  border-bottom: 1px solid var(--zivo-ink-30);
  font-size: 12px; line-height: 16px; text-transform: uppercase; letter-spacing: .04em;
}}

/* Hero */
.hero {{ background: var(--zivo-ink); color: var(--zivo-white); padding: 32px 0 48px; }}
.hero-inner {{ max-width: 1120px; margin: 0 auto; padding: 0 32px; }}
.hero .zv-header-row {{ border-bottom-color: rgba(255,255,255,.3); color: rgba(255,255,255,.8); }}
.hero h1 {{ color: var(--zivo-white); max-width: 22ch; }}
.hero-sub {{ margin: 16px 0 0; color: rgba(255,255,255,.7); font-family: var(--zivo-font-flare); font-size: 22px; line-height: 28px; max-width: 60ch; }}
.logo-tile {{ width: 56px; height: 56px; display: grid; place-items: center; background: var(--zivo-white); color: var(--zivo-ink); font-family: var(--zivo-font-flare); font-size: 28px; }}
.logo-tile img {{ max-width: 44px; max-height: 44px; }}

/* Page */
.page {{ max-width: 1120px; margin: 0 auto; padding: 48px 32px; }}
.section {{ margin-bottom: 48px; }}
.section > h2 {{ margin-bottom: 16px; }}

/* Cards */
.card {{ background: var(--zivo-white); border: 1px solid var(--zivo-ink-10); padding: 24px; }}
.card + .card {{ margin-top: var(--gap); }}
.card h3 {{ margin-bottom: 12px; }}

/* Stat strip */
.stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }}
.stat-card {{ background: var(--zivo-white); border: 1px solid var(--zivo-ink-10); padding: 20px; }}
.stat-card .value {{ font-family: var(--zivo-font-flare); font-size: 40px; line-height: 44px; margin-top: 8px; font-variant-numeric: tabular-nums; }}
.stat-card .value.accent {{ color: var(--zivo-red); }}
.stat-card .context {{ font-size: 14px; line-height: 20px; color: var(--zivo-ink-80); margin-top: 8px; }}
.trend-up {{ color: var(--zivo-success); }}
.trend-down {{ color: var(--zivo-error); }}
.trend-flat {{ color: var(--zivo-ink-60); }}

/* Big number: one per page */
.big-number .value {{ font-family: var(--zivo-font-flare); font-size: 96px; line-height: 92px; letter-spacing: -0.02em; }}
.big-number .rule {{ height: 1px; background: var(--zivo-ink); margin: 16px 0; }}
.big-number .label {{ font-size: 22px; line-height: 28px; text-transform: none; letter-spacing: 0; color: var(--zivo-ink); }}

/* Tables */
.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; line-height: 20px; background: var(--zivo-white); }}
thead th {{
  text-align: left; font-weight: 700; font-size: 12px; line-height: 16px;
  text-transform: uppercase; letter-spacing: .04em; color: var(--zivo-ink-80);
  border-bottom: 1px solid var(--zivo-ink-30); padding: 10px 12px;
}}
tbody td {{ padding: 10px 12px; border-bottom: 1px solid var(--zivo-ink-10); vertical-align: top; }}
tbody tr:last-child td {{ border-bottom: none; }}
td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}

/* Buttons: square, one arrow */
.btn {{
  display: inline-block; padding: 12px 16px; font-family: var(--zivo-font-sans); font-size: 16px; line-height: 20px;
  background: var(--zivo-ink); color: var(--zivo-white); border: 1px solid var(--zivo-ink);
  text-decoration: none; cursor: pointer;
}}
.btn:hover {{ background: #333; color: var(--zivo-white); }}
.btn-secondary {{ background: transparent; color: var(--zivo-ink); }}
.btn-secondary:hover {{ background: var(--zivo-ink-05); color: var(--zivo-ink); }}
.btn-primary {{ background: var(--zivo-red); border-color: var(--zivo-red); color: var(--zivo-white); }}
.btn-primary:hover {{ background: var(--zivo-red-hover); border-color: var(--zivo-red-hover); }}
.btn-primary:active {{ background: var(--zivo-red-pressed); }}

/* Badges: the only rounded element */
.badge {{ display: inline-block; white-space: nowrap; padding: 2px 10px; border-radius: 999px; font-size: 12px; line-height: 18px; font-weight: 700; background: var(--zivo-ink-05); color: var(--zivo-ink); }}
.badge-good {{ background: var(--zivo-success-bg); color: var(--zivo-success); }}
.badge-warn {{ background: var(--zivo-warning-bg); color: var(--zivo-warning); }}
.badge-bad  {{ background: var(--zivo-error-bg);   color: var(--zivo-error); }}
.badge-info {{ background: var(--zivo-info-bg);    color: var(--zivo-info); }}

/* Meters */
.meter {{ height: 8px; background: var(--zivo-ink-10); }}
.meter > span {{ display: block; height: 100%; background: var(--zivo-ink); }}

/* Callout: neutral note, no coloured side borders */
.callout {{ background: var(--zivo-white); border-top: 1px solid var(--zivo-ink); padding: 16px 0 0; }}

/* Footer */
.site-footer {{
  max-width: 1120px; margin: 0 auto; padding: 24px 32px 40px;
  display: flex; align-items: center; gap: 24px; flex-wrap: wrap;
  border-top: 1px solid var(--zivo-ink-10);
  font-size: 14px; line-height: 20px; color: var(--zivo-ink-60);
}}
.site-footer a {{ color: inherit; }}
.zv-wordmark {{ display: inline-flex; line-height: 0; }}
.zv-wordmark svg {{ height: 20px; width: auto; }}

@media (max-width: 560px) {{
  .hero-inner, .page, .site-footer {{ padding-left: 20px; padding-right: 20px; }}
  h1, .hero h1 {{ font-size: 36px; line-height: 36px; }}
  h2 {{ font-size: 26px; line-height: 30px; }}
  .zv-header-row {{ grid-template-columns: repeat(2, minmax(0, 1fr)); row-gap: 8px; }}
  .big-number .value {{ font-size: 64px; line-height: 64px; }}
}}

@media print {{
  body {{ background: var(--zivo-white); }}
  .hero {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
}}

/* Report components */
.grid-2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:24px;align-items:start}}
.grid-2 > .card + .card{{margin-top:0}}
.section-sub{{font-size:14px;line-height:20px;color:var(--zivo-ink-60);margin:-8px 0 16px}}
.insights{{list-style:none;margin:0;padding:0}}
.insights li{{display:flex;align-items:flex-start;padding:10px 0;border-bottom:1px solid var(--zivo-ink-10)}}
.insights li:first-child{{padding-top:0}}
.insights li:last-child{{border-bottom:none;padding-bottom:0}}
.insights .zv-dot{{flex:none;margin-top:8px}}
.hero .zv-header-row span{{min-width:0;overflow-wrap:anywhere}}
.callout{{padding:16px 20px;border-bottom:1px solid var(--zivo-ink-10)}}
.callout p:last-child{{margin-bottom:0}}
@media (max-width:560px){{.stat-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.stat-card .value{{font-size:32px;line-height:36px}}}}
td.num,th.num{{white-space:nowrap}}
@media (max-width:560px){{.card{{padding:16px}}.stat-card .value{{font-size:28px;line-height:32px;overflow-wrap:anywhere}}}}
.card h3{{margin-top:24px}}
.card h3:first-child{{margin-top:0}}
.card ul{{margin:0;padding-left:20px}}
.card li{{padding:4px 0}}
.scorecard-row{{display:grid;grid-template-columns:1fr auto;gap:16px;padding:12px 0;border-bottom:1px solid var(--zivo-ink-10);align-items:center}}
.scorecard-row:last-child{{border-bottom:none}}
.rubric{{font-size:14px;line-height:20px;color:var(--zivo-ink-60);margin-top:4px}}
.question{{padding:16px 0;border-bottom:1px solid var(--zivo-ink-10)}}
.question:first-child{{padding-top:0}}
.question:last-child{{border-bottom:none;padding-bottom:0}}
.question .badge{{margin-bottom:8px}}
.look-for{{font-size:14px;line-height:20px;color:var(--zivo-ink-80);margin-top:4px}}
</style></head>
<body>

<header class="hero">
<div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>Job profile</span><span>Recrutamento</span><span>Uso interno</span></div>
<h1>{role}</h1>
<p class="hero-sub">{meta}</p>
</div>
</header>

<main class="page">
{body}
</main>

<footer class="site-footer">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=job-profile-builder" aria-label="Zivo"><svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg></a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer>
</body></html>
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
        parts.append('<section class="section"><h2>Resumo executivo</h2><div class="card">')
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
        parts.append("</div></section>")

    jd = data.get("jd") or {}
    if jd:
        parts.append('<section class="section"><h2>Job description</h2><div class="card">')
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
        parts.append("</div></section>")

    scorecard = data.get("scorecard") or []
    if scorecard:
        parts.append('<section class="section"><h2>Scorecard de avaliação</h2>')
        parts.append('<p class="section-sub">Cada entrevistador pontua cada critério de 1-5. Soma ponderada pelo peso.</p><div class="card">')
        for s in scorecard:
            parts.append(f'<div class="scorecard-row">')
            parts.append(f'<div><strong>{_esc(s.get("criterion"))}</strong>')
            if s.get("rubric"):
                parts.append(f'<div class="rubric">{_esc(s["rubric"])}</div>')
            parts.append('</div>')
            parts.append(f'<span class="badge">Peso {_esc(s.get("weight", "—"))}</span>')
            parts.append('</div>')
        parts.append("</div></section>")

    questions = data.get("interview_questions") or []
    if questions:
        parts.append('<section class="section"><h2>Roteiro de entrevistas</h2><div class="card">')
        for q in questions:
            parts.append('<div class="question">')
            if q.get("stage"):
                parts.append(f'<span class="badge badge-info">{_esc(q["stage"])}</span>')
            parts.append(f'<div><strong>{_esc(q.get("question"))}</strong></div>')
            if q.get("what_to_look_for"):
                parts.append(f'<div class="look-for"><strong>O que procurar:</strong> {_esc(q["what_to_look_for"])}</div>')
            parts.append("</div>")
        parts.append("</div></section>")

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

    lines.append("\n---\n— Powered by Zivo · https://zivo.ai?utm_source=skill-output&utm_medium=md-footer&utm_campaign=eam&utm_content=job-profile-builder")
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

    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=job-profile-builder")
    return 0


# Workaround for type annotation (Any)
from typing import Any  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
