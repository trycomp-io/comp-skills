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


# ---------- Zivo visual (zivo-html-guidelines) ----------
ZIVO_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Marcellus&family=Source+Sans+3:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">'
)

ZIVO_CSS = """
:root {
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
}
* { box-sizing: border-box; border-radius: 0; box-shadow: none; }
body {
  margin: 0;
  font-family: var(--zivo-font-sans);
  font-size: 16px;
  line-height: 1.5;
  color: var(--zivo-ink);
  background: var(--zivo-off-white);
  -webkit-font-smoothing: antialiased;
}
h1, h2, h3, h4 {
  font-family: var(--zivo-font-flare);
  font-weight: 400;
  font-style: normal;
  text-transform: none;
  margin: 0 0 .4em;
}
h1 { font-size: 56px; line-height: 54px; letter-spacing: -0.02em; }
h2 { font-size: 32px; line-height: 36px; letter-spacing: -0.01em; }
h3 { font-size: 22px; line-height: 28px; }
h4 { font-size: 18px; line-height: 24px; }
p { margin: 0 0 1em; }
small, .small { font-size: 14px; line-height: 20px; }
.caption, .label {
  font-size: 12px; line-height: 16px; text-transform: uppercase;
  letter-spacing: .04em; color: var(--zivo-ink-60);
}
.muted { color: var(--zivo-ink-60); }
a { color: var(--zivo-ink); text-decoration: underline; text-underline-offset: 2px; }
a:hover { color: var(--zivo-ink-80); }
.zv-dot { display: inline-block; width: 8px; height: 8px; background: currentColor; margin-right: 8px; vertical-align: 1px; }
.zv-dot--red { background: var(--zivo-red); }
.zv-header-row {
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--gap);
  padding-bottom: 10px; margin-bottom: 40px;
  border-bottom: 1px solid var(--zivo-ink-30);
  font-size: 12px; line-height: 16px; text-transform: uppercase; letter-spacing: .04em;
}
.hero { background: var(--zivo-ink); color: var(--zivo-white); padding: 32px 0 48px; }
.hero-inner { max-width: 1120px; margin: 0 auto; padding: 0 32px; }
.hero .zv-header-row { border-bottom-color: rgba(255,255,255,.3); color: rgba(255,255,255,.8); }
.hero h1 { color: var(--zivo-white); max-width: 22ch; }
.hero-sub { margin: 16px 0 0; color: rgba(255,255,255,.7); font-family: var(--zivo-font-flare); font-size: 22px; line-height: 28px; max-width: 60ch; }
.hero-main { display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; }
.logo-tile { width: 56px; height: 56px; display: grid; place-items: center; background: var(--zivo-white); color: var(--zivo-ink); font-family: var(--zivo-font-flare); font-size: 28px; }
.logo-tile img { max-width: 44px; max-height: 44px; }
.page { max-width: 1120px; margin: 0 auto; padding: 48px 32px; }
.section { margin-bottom: 48px; }
.section > h2 { margin-bottom: 16px; }
.card { background: var(--zivo-white); border: 1px solid var(--zivo-ink-10); padding: 24px; }
.card + .card { margin-top: var(--gap); }
.card h3 { margin-bottom: 12px; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
.stat-card { background: var(--zivo-white); border: 1px solid var(--zivo-ink-10); padding: 20px; }
.stat-card .value { font-family: var(--zivo-font-flare); font-size: 40px; line-height: 44px; margin-top: 8px; font-variant-numeric: tabular-nums; }
.stat-card .value.accent { color: var(--zivo-red); }
.stat-card .context { font-size: 14px; line-height: 20px; color: var(--zivo-ink-80); margin-top: 8px; }
.trend-up { color: var(--zivo-success); }
.trend-down { color: var(--zivo-error); }
.trend-flat { color: var(--zivo-ink-60); }
.big-number .value { font-family: var(--zivo-font-flare); font-size: 96px; line-height: 92px; letter-spacing: -0.02em; }
.big-number .rule { height: 1px; background: var(--zivo-ink); margin: 16px 0; }
.big-number .label { font-size: 22px; line-height: 28px; text-transform: none; letter-spacing: 0; color: var(--zivo-ink); }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; line-height: 20px; background: var(--zivo-white); }
thead th {
  text-align: left; font-weight: 700; font-size: 12px; line-height: 16px;
  text-transform: uppercase; letter-spacing: .04em; color: var(--zivo-ink-80);
  border-bottom: 1px solid var(--zivo-ink-30); padding: 10px 12px;
}
tbody td { padding: 10px 12px; border-bottom: 1px solid var(--zivo-ink-10); vertical-align: top; }
tbody tr:last-child td { border-bottom: none; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.btn {
  display: inline-block; padding: 12px 16px; font-family: var(--zivo-font-sans); font-size: 16px; line-height: 20px;
  background: var(--zivo-ink); color: var(--zivo-white); border: 1px solid var(--zivo-ink);
  text-decoration: none; cursor: pointer;
}
.btn:hover { background: #333; color: var(--zivo-white); }
.btn-secondary { background: transparent; color: var(--zivo-ink); }
.btn-secondary:hover { background: var(--zivo-ink-05); color: var(--zivo-ink); }
.btn-primary { background: var(--zivo-red); border-color: var(--zivo-red); color: var(--zivo-white); }
.btn-primary:hover { background: var(--zivo-red-hover); border-color: var(--zivo-red-hover); }
.btn-primary:active { background: var(--zivo-red-pressed); }
.badge { display: inline-block; white-space: nowrap; padding: 2px 10px; border-radius: 999px; font-size: 12px; line-height: 18px; font-weight: 700; background: var(--zivo-ink-05); color: var(--zivo-ink); }
.badge-good { background: var(--zivo-success-bg); color: var(--zivo-success); }
.badge-warn { background: var(--zivo-warning-bg); color: var(--zivo-warning); }
.badge-bad  { background: var(--zivo-error-bg);   color: var(--zivo-error); }
.badge-info { background: var(--zivo-info-bg);    color: var(--zivo-info); }
.meter { height: 8px; background: var(--zivo-ink-10); }
.meter > span { display: block; height: 100%; background: var(--zivo-ink); }
.callout { background: var(--zivo-white); border-top: 1px solid var(--zivo-ink); padding: 16px 0 0; }
.site-footer {
  max-width: 1120px; margin: 0 auto; padding: 24px 32px 40px;
  display: flex; align-items: center; gap: 24px; flex-wrap: wrap;
  border-top: 1px solid var(--zivo-ink-10);
  font-size: 14px; line-height: 20px; color: var(--zivo-ink-60);
}
.site-footer a { color: inherit; }
.zv-wordmark { display: inline-flex; line-height: 0; }
.zv-wordmark svg { height: 20px; width: auto; }
@media (max-width: 560px) {
  .hero-inner, .page, .site-footer { padding-left: 20px; padding-right: 20px; }
  h1, .hero h1 { font-size: 36px; line-height: 36px; }
  h2 { font-size: 26px; line-height: 30px; }
  .zv-header-row { grid-template-columns: repeat(2, minmax(0, 1fr)); row-gap: 8px; }
  .big-number .value { font-size: 64px; line-height: 64px; }
}
@media print {
  body { background: var(--zivo-white); }
  .hero { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
"""

ZIVO_WORDMARK = (
    '<svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg>'
)


def _zivo_footer(slug: str) -> str:
    return (
        '<footer class="site-footer">'
        '<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer'
        f'&amp;utm_campaign=eam&amp;utm_content={slug}" aria-label="Zivo">{ZIVO_WORDMARK}</a>'
        '<span>Powered by Zivo · free skills for HR &amp; People leaders</span>'
        '</footer>'
    )


def _zivo_hero(captions, title: str, sub: str = "", aside: str = "") -> str:
    """Ink hero band. All arguments must already be HTML-escaped."""
    caps = "".join(
        (f'<span><i class="zv-dot zv-dot--red"></i>{c}</span>' if i == 0 else f"<span>{c}</span>")
        for i, c in enumerate(["Zivo"] + [c for c in captions if c][:3])
    )
    sub_html = f'<p class="hero-sub">{sub}</p>' if sub else ""
    body = f"<div><h1>{title}</h1>{sub_html}</div>"
    if aside:
        body = f'<div class="hero-main">{body}{aside}</div>'
    return (
        '<header class="hero"><div class="hero-inner">'
        f'<div class="zv-header-row">{caps}</div>{body}'
        "</div></header>"
    )
# ---------------------------------------------------------


def _slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip()).strip("-").lower()[:50] or "slide"


def _esc(s):
    if s is None: return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


HTML = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Board people slide · {period} · Zivo</title>
{zivo_fonts}
<style>{zivo_css}</style>
<style>
  body{{padding:32px;min-height:100vh;display:flex;align-items:center;justify-content:center}}
  .stage{{width:100%;max-width:1920px;container-type:inline-size}}
  .slide{{width:100%;aspect-ratio:16/9;background:var(--zivo-white);border:1px solid var(--zivo-ink-10);padding:4.2cqw 4.6cqw 3cqw;display:flex;flex-direction:column;overflow:hidden}}
  .slide .zv-header-row{{font-size:.85cqw;line-height:1.2cqw;margin-bottom:2.6cqw;padding-bottom:.6cqw;color:var(--zivo-ink-80)}}
  .slide h1{{font-size:4.4cqw;line-height:4.4cqw;max-width:30ch;margin:0}}
  .kpis{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1.7cqw;margin:3cqw 0 2.6cqw}}
  .kpi{{border-top:1px solid var(--zivo-ink);padding-top:1cqw}}
  .kpi-label{{font-size:.75cqw;line-height:1.1cqw;text-transform:uppercase;letter-spacing:.04em;color:var(--zivo-ink-60)}}
  .kpi-val{{font-family:var(--zivo-font-flare);font-size:3.6cqw;line-height:3.8cqw;margin-top:.6cqw;font-variant-numeric:tabular-nums}}
  .kpi-trend{{font-family:var(--zivo-font-sans);font-size:1.6cqw;margin-left:.5cqw}}
  .kpi-context{{font-size:.85cqw;line-height:1.2cqw;color:var(--zivo-ink-80);margin-top:.5cqw}}
  .lower{{display:grid;grid-template-columns:2fr 1fr;gap:3cqw;flex:1;min-height:0}}
  .lower h3{{font-size:1.4cqw;line-height:1.8cqw;margin:0 0 .6cqw}}
  .highlight{{padding:.7cqw 0;font-size:1.05cqw;line-height:1.5cqw;border-top:1px solid var(--zivo-ink-10)}}
  .highlight .zv-dot{{width:.45cqw;height:.45cqw;margin-right:.7cqw;vertical-align:.12cqw}}
  .ask{{border-top:1px solid var(--zivo-ink-10);padding:.7cqw 0;font-size:1cqw;line-height:1.45cqw}}
  .ask .kpi-label{{display:block;margin-bottom:.2cqw}}
  .slide-footer{{display:flex;justify-content:space-between;align-items:flex-end;gap:2cqw;margin-top:auto;padding-top:1.2cqw;border-top:1px solid var(--zivo-ink-10);font-size:.75cqw;line-height:1.1cqw;color:var(--zivo-ink-60)}}
  .slide-footer .left{{display:flex;align-items:flex-end;gap:1.4cqw}}
  .slide-footer .zv-wordmark svg{{height:1.5cqw;min-height:16px}}
  .slide-footer a{{color:inherit}}
  @media (max-width:700px){{
    body{{padding:16px;display:block}}
    .slide{{aspect-ratio:auto;padding:24px 20px}}
    .slide .zv-header-row{{font-size:12px;line-height:16px;margin-bottom:24px;padding-bottom:8px;grid-template-columns:repeat(2,minmax(0,1fr))}}
    .slide h1{{font-size:32px;line-height:34px}}
    .kpis{{grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:24px 0}}
    .kpi{{padding-top:8px}}
    .kpi-label{{font-size:12px;line-height:16px}}
    .kpi-val{{font-size:30px;line-height:34px;margin-top:4px}}
    .kpi-trend{{font-size:18px;margin-left:4px}}
    .kpi-context{{font-size:13px;line-height:18px}}
    .lower{{grid-template-columns:1fr;gap:24px}}
    .lower h3{{font-size:20px;line-height:26px;margin-bottom:8px}}
    .highlight,.ask{{font-size:15px;line-height:22px;padding:8px 0}}
    .highlight .zv-dot{{width:8px;height:8px;margin-right:8px;vertical-align:1px}}
    .slide-footer{{flex-direction:column;align-items:flex-start;font-size:12px;line-height:16px;padding-top:16px;margin-top:24px}}
    .slide-footer .left{{flex-direction:column;align-items:flex-start;gap:8px}}
    .slide-footer .zv-wordmark svg{{height:20px}}
  }}
  @page{{size:1920px 1080px;margin:0}}
  @media print{{body{{padding:0;display:block}} .slide{{border:none}}}}
</style></head>
<body>
<div class="stage"><div class="slide">

<header>
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>{eyebrow}</span><span>{company_caption}</span><span>{period}</span></div>
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

<div class="slide-footer">
<div class="left">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=board-people-slide-builder" aria-label="Zivo">{wordmark}</a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</div>
<div>{company} · People &amp; Culture · {period}</div>
</div>

</div></div></body></html>
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
        trend = trend if trend in ("up", "down", "flat") else "flat"
        arrow = {"up": "↗", "down": "↘", "flat": "→"}.get(trend, "→")
        context = k.get("context")
        context_html = f'<div class="kpi-context">{_esc(context)}</div>' if context else ""
        kpis_html.append(
            f'<div class="kpi">'
            f'<div class="kpi-label">{_esc(k.get("label"))}</div>'
            f'<div class="kpi-val">{_esc(k.get("value"))}<span class="kpi-trend trend-{trend}">{arrow}</span></div>'
            f'{context_html}'
            f'</div>'
        )

    highlights = data.get("highlights", [])
    highlights_html = "".join(f'<div class="highlight"><i class="zv-dot"></i>{_esc(h)}</div>' for h in highlights)

    risks_html = []
    for r in data.get("risks", []):
        risks_html.append(f'<div class="ask"><span class="kpi-label">Risco</span>{_esc(r)}</div>')
    for a in data.get("asks", []):
        risks_html.append(f'<div class="ask"><span class="kpi-label">Ask</span>{_esc(a)}</div>')
    risks_asks_html = "<h3>Riscos &amp; Asks</h3>" + "".join(risks_html) if risks_html else ""

    return HTML.format(
        period=period, company=company, title=title, eyebrow=eyebrow,
        company_caption=company or "People &amp; Culture",
        zivo_fonts=ZIVO_FONTS, zivo_css=ZIVO_CSS, wordmark=ZIVO_WORDMARK,
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
    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=board-people-slide-builder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
