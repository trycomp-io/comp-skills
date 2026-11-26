#!/usr/bin/env python3
"""
render_pack.py — Renderiza pacote defensável de comp budget pra CHRO levar
ao CFO/CEO. Estrutura cada linha do pedido (% reajuste, novas vagas, ajustes
pontuais) com justificativa, benchmark, custo total e cenários alternativos.

Schema JSON:
{
  "period": "H2 2026",
  "ask_summary": "Pedido total de R$ X em comp/headcount no H2",
  "total_request_brl": 1500000,
  "current_payroll_brl_monthly": 800000,
  "items": [
    {
      "category": "reajuste|hire|adjustment",
      "label": "Reajuste de mérito 5% no time de Eng",
      "rationale": "Inflação 4%, mercado Eng pagando +15% acima da empresa, retenção em risco",
      "benchmark_source": "Robert Half / Mercer",
      "headcount_affected": 30,
      "cost_monthly": 24000,
      "cost_annual_loaded": 449000
    }
  ],
  "scenarios": [
    {"name": "Pedido completo", "cost": 1500000, "outcome": "..."},
    {"name": "50% do pedido", "cost": 750000, "outcome": "..."}
  ],
  "risks_if_denied": ["..."],
  "asks_decision": "Aprovar R$ X até DATA"
}

Uso:
    cat pack.json | python3 render_pack.py
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

SKILL_NAME = "comp-budget-defense-pack"
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
    return re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip()).strip("-").lower()[:50] or "pack"


def _esc(s):
    if s is None: return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _money(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "—"


CAT_LABELS = {"reajuste": ("Reajuste", ""),
              "hire": ("Hire", ""),
              "adjustment": ("Ajuste pontual", "")}


HTML = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Comp budget defense pack · {period} · Zivo</title>
{zivo_fonts}
<style>{zivo_css}</style>
<style>
  .stat-card .value{{font-size:32px;line-height:38px;white-space:nowrap}}
  td.num,th.num{{white-space:nowrap}}
  td.item{{min-width:140px}}
  td.why{{min-width:200px}}
  .bench{{display:block;font-size:12px;line-height:16px;color:var(--zivo-ink-60);margin-top:4px}}
  .scenario{{display:flex;justify-content:space-between;align-items:baseline;gap:16px;padding:12px 0;border-top:1px solid var(--zivo-ink-10)}}
  .scenario:first-child{{border-top:none;padding-top:0}}
  .scenario .outcome{{font-size:14px;line-height:20px;color:var(--zivo-ink-80);margin-top:2px}}
  .scenario .cost{{font-family:var(--zivo-font-flare);font-size:24px;line-height:28px;white-space:nowrap;font-variant-numeric:tabular-nums}}
  .rows{{list-style:none;padding:0;margin:0}}
  .rows li{{padding:10px 0;border-top:1px solid var(--zivo-ink-10)}}
  .rows li:first-child{{border-top:none;padding-top:0}}
  .ask{{background:var(--zivo-ink);color:var(--zivo-white);padding:24px;font-size:18px;line-height:28px}}
  .ask .label{{color:rgba(255,255,255,.7);display:block;margin-bottom:8px}}
  @media (max-width:560px){{.scenario{{flex-direction:column;gap:4px}}}}
</style></head>
<body>
{hero}
<main class="page">

<section class="section">
<div class="stat-grid">
<div class="stat-card"><div class="label">Pedido total</div><div class="value accent">{total_request}</div><div class="context">Soma das linhas do pedido.</div></div>
<div class="stat-card"><div class="label">Folha atual (mensal)</div><div class="value">{current_payroll}</div><div class="context">Base de comparação.</div></div>
<div class="stat-card"><div class="label">% impacto na folha</div><div class="value">{pct_impact}</div><div class="context">Pedido sobre 12 meses de folha.</div></div>
</div>
</section>

<section class="section">
<h2>Linhas do pedido (justificadas)</h2>
<div class="card table-wrap"><table><thead><tr><th>Categoria</th><th>Item</th><th class="num">HC</th><th class="num">Mensal</th><th class="num">Anual c/ encargos</th><th>Justificativa</th></tr></thead><tbody>
{items_html}
</tbody></table></div>
</section>

<section class="section">
<h2>Cenários</h2>
<div class="card">
{scenarios_html}
</div>
</section>

{risks_html}

<section class="section">
<h2>Ask</h2>
<div class="ask"><span class="label">Decisão pedida</span>{asks_decision}</div>
</section>

</main>
{footer}
</body></html>
"""


def render_html(d):
    period = _esc(d.get("period", ""))
    ask_summary = _esc(d.get("ask_summary", ""))
    total_request = _money(d.get("total_request_brl"))
    current_payroll = _money(d.get("current_payroll_brl_monthly"))
    pct_impact = "—"
    try:
        if d.get("current_payroll_brl_monthly") and d.get("total_request_brl"):
            pct_impact = f"{(float(d['total_request_brl']) / (float(d['current_payroll_brl_monthly']) * 12) * 100):.1f}%"
    except (TypeError, ValueError):
        pass

    items_html = []
    for it in d.get("items", []):
        cat = it.get("category", "")
        label, cls = CAT_LABELS.get(cat, (_esc(cat) or "—", ""))
        bench = f' <span class="bench">Fonte: {_esc(it.get("benchmark_source"))}</span>' if it.get("benchmark_source") else ""
        items_html.append(
            f"<tr>"
            f'<td><span class="badge {cls}">{label}</span></td>'
            f"<td class='item'><strong>{_esc(it.get('label'))}</strong></td>"
            f"<td class='num'>{_esc(it.get('headcount_affected', '—'))}</td>"
            f"<td class='num'>{_money(it.get('cost_monthly'))}</td>"
            f"<td class='num'>{_money(it.get('cost_annual_loaded'))}</td>"
            f"<td class='why'>{_esc(it.get('rationale'))}{bench}</td>"
            f"</tr>"
        )

    scenarios_html = []
    for s in d.get("scenarios", []):
        scenarios_html.append(
            f'<div class="scenario">'
            f'<div><strong>{_esc(s.get("name"))}</strong>'
            f'<div class="outcome">{_esc(s.get("outcome"))}</div></div>'
            f'<div class="cost">{_money(s.get("cost"))}</div>'
            f'</div>'
        )

    risks_html = ""
    if d.get("risks_if_denied"):
        risks_html = '<section class="section"><h2>Riscos se negado</h2><div class="card"><ul class="rows">' + \
                     "".join(f'<li><span class="badge badge-bad">Risco</span> {_esc(r)}</li>' for r in d["risks_if_denied"]) + \
                     '</ul></div></section>'

    hero = _zivo_hero(
        ["Comp budget defense pack", period, "Confidencial"],
        f"Pedido de {total_request} em comp e headcount" + (f" no {period}" if period else ""),
        ask_summary,
    )
    return HTML.format(
        zivo_fonts=ZIVO_FONTS, zivo_css=ZIVO_CSS, hero=hero, footer=_zivo_footer(SKILL_NAME),
        period=period,
        total_request=total_request, current_payroll=current_payroll, pct_impact=pct_impact,
        items_html="\n".join(items_html) or '<tr><td colspan="6">—</td></tr>',
        scenarios_html="\n".join(scenarios_html),
        risks_html=risks_html,
        asks_decision=_esc(d.get("asks_decision", "")),
    )


def main():
    p = argparse.ArgumentParser(description="Renderiza Comp Budget Defense Pack.")
    p.add_argument("--input", type=Path); p.add_argument("--output", type=Path)
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
    slug = _slug(d.get("period", "pack"))
    out = args.output or Path.cwd() / f"comp-budget-pack-{slug}-{ts}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(d), encoding="utf-8")
    print(f"Gerado: {out}")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=comp-budget-defense-pack")
    return 0


if __name__ == "__main__":
    sys.exit(main())
