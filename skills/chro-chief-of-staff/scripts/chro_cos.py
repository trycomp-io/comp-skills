#!/usr/bin/env python3
"""
chro_cos.py — Chief of Staff do CHRO. Mantém contexto persistente, gerencia
open loops, renderiza briefs/drafts/prompts gerados pelo Claude.

A INTELIGÊNCIA estratégica (gerar brief, draft, prompt) vem do Claude
seguindo SKILL.md. Este script faz a parte mecânica:
- Setup (wizard inicial)
- Show (estado atual)
- Loops (add, list, close, persiste)
- Render (HTML+MD a partir de JSON do Claude)

Config persistido em ~/.zivo-skills/chro-context.json.

Comandos:
    chro_cos.py setup
    chro_cos.py show
    chro_cos.py loop add --description "..." --owner "..." --due 2026-06-15
    chro_cos.py loop list [--all]
    chro_cos.py loop close <id>
    chro_cos.py render-brief --input brief.json [--output ...]
    chro_cos.py render-draft --input draft.json [--output ...]
    chro_cos.py render-week --input week.json [--output ...]
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "chro-chief-of-staff"
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

CONFIG_DIR = Path.home() / ".zivo-skills"
CONFIG_PATH = CONFIG_DIR / "chro-context.json"

DEFAULT_CADENCES = {
    "ceo_1on1": "weekly",
    "elt_meeting": "weekly",
    "people_lt_meeting": "weekly",
    "monthly_ceo_update": "monthly",
    "talent_review": "monthly",
    "skip_levels": "monthly",
    "board": "quarterly",
    "comp_committee": "quarterly",
    "engagement_pulse": "quarterly",
    "okr_review": "quarterly",
    "comp_cycle": "biannual",
    "workforce_planning": "biannual",
    "perf_cycle": "annual",
    "annual_budget": "annual",
    "engagement_major_survey": "annual",
}

DEFAULT_LANGUAGE = "pt-BR"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_chro_section(cfg: dict) -> dict:
    cfg.setdefault("chro", {})
    cfg.setdefault("key_stakeholders", [])
    cfg.setdefault("cadences", dict(DEFAULT_CADENCES))
    cfg.setdefault("active_initiatives", [])
    cfg.setdefault("open_loops", [])
    cfg.setdefault("key_calendar_events", [])
    return cfg


# ========== SETUP wizard ==========


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        v = input(f"{label}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        v = ""
    return v or default


def cmd_setup() -> int:
    print("=" * 60)
    print("CHRO Chief of Staff — setup")
    print("=" * 60)
    cfg = ensure_chro_section(load_config())

    print("\n## Sobre você")
    cfg["chro"]["name"] = _prompt("Seu nome", cfg["chro"].get("name", ""))
    cfg["chro"]["company"] = _prompt("Empresa", cfg["chro"].get("company", ""))
    cfg["chro"]["language_preference"] = _prompt(
        "Idioma preferido (pt-BR ou en)",
        cfg["chro"].get("language_preference", DEFAULT_LANGUAGE),
    ) or DEFAULT_LANGUAGE
    cfg["chro"]["current_quarter"] = _prompt(
        "Trimestre atual (ex: Q2 2026)", cfg["chro"].get("current_quarter", "")
    )

    print("\n## Stakeholders-chave (CEO, CFO, peers, diretos)")
    print("Adicione os principais. Enter vazio em qualquer pergunta termina.")
    existing = cfg.get("key_stakeholders", [])
    if existing:
        print(f"Já cadastrados: {len(existing)} — pressione Enter pra manter ou redigite.")
    new_stake = []
    while True:
        name = _prompt("\n  Nome (Enter pra terminar)")
        if not name:
            break
        role = _prompt("  Papel (ex: CEO, CFO, Head of TA)")
        rel = _prompt("  Relação (boss / peer / report)", "peer")
        new_stake.append({"name": name, "role": role, "relationship": rel})
    if new_stake:
        cfg["key_stakeholders"] = new_stake
    elif not existing:
        cfg["key_stakeholders"] = []

    print("\n## Próximos eventos do calendário (board meeting, comp cycle, etc.)")
    print("Adicione os principais. Enter vazio termina.")
    new_events = []
    while True:
        evt = _prompt("\n  Evento (Enter pra terminar)")
        if not evt:
            break
        d = _prompt("  Data (YYYY-MM-DD)")
        new_events.append({"event": evt, "date": d})
    if new_events:
        cfg["key_calendar_events"] = new_events

    print("\n## Cadências")
    print("Estamos usando defaults. Customize editando ~/.zivo-skills/chro-context.json depois se quiser.")

    save_config(cfg)
    print(f"\nConfig salvo em {CONFIG_PATH}")
    print("Pronto. Agora você pode pedir ao Claude: 'me dá o brief da reunião X', 'qual minha semana', etc.")
    return 0


# ========== SHOW ==========


def cmd_show() -> int:
    cfg = load_config()
    if not cfg:
        print(f"Sem config. Rode: chro_cos.py setup")
        return 1
    print(json.dumps(cfg, indent=2, ensure_ascii=False))
    return 0


# ========== LOOPS ==========


def cmd_loop_add(args) -> int:
    cfg = ensure_chro_section(load_config())
    loop = {
        "id": "loop-" + uuid.uuid4().hex[:6],
        "description": args.description,
        "owner": args.owner or cfg.get("chro", {}).get("name", ""),
        "due": args.due or "",
        "status": "open",
        "created_at": date.today().isoformat(),
    }
    cfg["open_loops"].append(loop)
    save_config(cfg)
    print(f"Adicionado: {loop['id']} — {loop['description']}")
    return 0


def cmd_loop_list(args) -> int:
    cfg = load_config()
    loops = cfg.get("open_loops", [])
    if not args.all:
        loops = [l for l in loops if l.get("status") == "open"]
    if not loops:
        print("Nenhum open loop." + (" (use --all pra ver fechados também)" if not args.all else ""))
        return 0
    for l in loops:
        status_label = "[FECHADO]" if l.get("status") != "open" else "[ABERTO]"
        due = f" (due {l['due']})" if l.get("due") else ""
        owner = f" — {l['owner']}" if l.get("owner") else ""
        print(f"  {status_label} {l['id']}{owner}: {l['description']}{due}")
    return 0


def cmd_loop_close(args) -> int:
    cfg = load_config()
    found = False
    for l in cfg.get("open_loops", []):
        if l.get("id") == args.loop_id:
            l["status"] = "closed"
            l["closed_at"] = date.today().isoformat()
            found = True
            break
    if not found:
        print(f"ID não encontrado: {args.loop_id}")
        return 1
    save_config(cfg)
    print(f"Fechado: {args.loop_id}")
    return 0


# ========== RENDER HELPERS ==========


def _esc(s):
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


BRIEF_HTML = """<!DOCTYPE html>
<html lang="{lang}"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Zivo</title>
{zivo_fonts}
<style>{zivo_css}</style>
<style>
  .page,.hero-inner,.site-footer{{max-width:880px}}
  .meta{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-bottom:48px}}
  .meta div{{border-top:1px solid var(--zivo-ink);padding-top:8px;overflow-wrap:anywhere}}
  .meta .label{{display:block;margin-bottom:4px}}
  .section > .card ul{{margin:0;padding-left:20px}}
  .section > .card li{{padding:3px 0}}
  .rows{{list-style:none;padding:0;margin:0}}
  .rows li{{padding:10px 0;border-top:1px solid var(--zivo-ink-10)}}
  .rows li:first-child{{border-top:none;padding-top:0}}
  .section > .card ul.rows{{padding-left:0}}
  .section > .card ul.rows li{{padding:10px 0}}
  .section > .card ul.rows li:first-child{{padding-top:0}}
</style></head>
<body>
{hero}
<main class="page">
{meta}
{body}
</main>
{footer}
</body></html>
"""


def _section(title: str, items, kind: str = "list") -> str:
    if not items:
        return ""
    if kind == "list":
        body = "<ul>" + "".join(f"<li>{_esc(i)}</li>" for i in items) + "</ul>"
    elif kind == "talking-points":
        body = '<ul class="rows">' + "".join(f'<li><i class="zv-dot"></i>{_esc(i)}</li>' for i in items) + "</ul>"
    elif kind == "asks":
        body = '<ul class="rows">' + "".join(f'<li><span class="badge">Ask</span> {_esc(i)}</li>' for i in items) + "</ul>"
    else:
        body = '<p style="margin:0">' + _esc(items) + "</p>"
    return f'<section class="section"><h2>{_esc(title)}</h2><div class="card">{body}</div></section>'


def render_brief_html(data: dict, lang: str) -> str:
    title = data.get("title", "Pre-meeting Brief")
    meta_parts = []
    for k in ("meeting", "date", "participants"):
        if data.get(k):
            v = data[k]
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            meta_parts.append(f'<div><span class="label">{k}</span>{_esc(v)}</div>')
    meta = f'<div class="meta">{"".join(meta_parts)}</div>' if meta_parts else ""

    body = []
    sections = data.get("sections", [])
    for sec in sections:
        sec_title = sec.get("title", "")
        kind = sec.get("kind", "list")
        items = sec.get("items", [])
        body.append(_section(sec_title, items, kind))

    hero = _zivo_hero(
        ["CHRO chief of staff", _esc(data.get("meeting", "")), _esc(data.get("date", ""))],
        _esc(title),
    )
    return BRIEF_HTML.format(
        lang=_esc(lang), title=_esc(title), meta=meta, body="\n".join(body),
        zivo_fonts=ZIVO_FONTS, zivo_css=ZIVO_CSS, hero=hero, footer=_zivo_footer(SKILL_NAME),
    )


def render_brief_md(data: dict) -> str:
    lines = [f"# {data.get('title', 'Pre-meeting Brief')}\n"]
    for k in ("meeting", "date", "participants"):
        if data.get(k):
            v = data[k]
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            lines.append(f"**{k}:** {v}")
    lines.append("")
    for sec in data.get("sections", []):
        lines.append(f"\n## {sec.get('title', '')}\n")
        for item in sec.get("items", []):
            lines.append(f"- {item}")
    lines.append("\n---\n— Powered by Zivo · https://zivo.ai?utm_source=skill-output&utm_medium=md-footer&utm_campaign=eam&utm_content=chro-chief-of-staff")
    return "\n".join(lines)


def cmd_render_brief(args) -> int:
    if args.input:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        if sys.stdin.isatty():
            print("Forneça --input ou pipe JSON via stdin.", file=sys.stderr)
            return 1
        data = json.loads(sys.stdin.read())

    cfg = load_config()
    lang = data.get("language") or cfg.get("chro", {}).get("language_preference", DEFAULT_LANGUAGE)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_html = args.output or Path.cwd() / f"chro-brief-{ts}.html"
    out_md = args.markdown_output or out_html.with_suffix(".md")
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(render_brief_html(data, lang), encoding="utf-8")
    out_md.write_text(render_brief_md(data), encoding="utf-8")
    print(f"Gerado HTML: {out_html}\nGerado MD:   {out_md}")
    return 0


DRAFT_HTML = """<!DOCTYPE html>
<html lang="{lang}"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Zivo</title>
{zivo_fonts}
<style>{zivo_css}</style>
<style>
  .page,.hero-inner,.site-footer{{max-width:880px}}
  .meta{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-bottom:48px}}
  .meta div{{border-top:1px solid var(--zivo-ink);padding-top:8px;overflow-wrap:anywhere}}
  .meta .label{{display:block;margin-bottom:4px}}
  .draft{{white-space:pre-wrap;font-size:16px;line-height:26px}}
  .alt{{margin-top:32px}}
  .alt .label{{display:block;margin-bottom:8px}}
</style></head>
<body>
{hero}
<main class="page">
{meta}
{body}
</main>
{footer}
</body></html>
"""


def render_draft_html(data: dict, lang: str) -> str:
    title = data.get("subject") or data.get("topic") or "Draft"
    meta_parts = []
    for k in ("type", "to", "from", "tone"):
        if data.get(k):
            meta_parts.append(f'<div><span class="label">{k}</span>{_esc(data[k])}</div>')
    meta = f'<div class="meta">{"".join(meta_parts)}</div>' if meta_parts else ""

    body = []
    primary = data.get("draft", "")
    body.append(f'<div class="card"><div class="draft">{_esc(primary)}</div></div>')

    for i, alt in enumerate(data.get("alternatives", []), 1):
        body.append(f'<div class="alt"><span class="label">Alternativa {i}</span><div class="card"><div class="draft">{_esc(alt)}</div></div></div>')

    hero = _zivo_hero(
        ["CHRO chief of staff", "Draft", _esc(data.get("type", ""))],
        _esc(title),
    )
    return DRAFT_HTML.format(
        lang=_esc(lang), title=_esc(title), meta=meta, body="\n".join(body),
        zivo_fonts=ZIVO_FONTS, zivo_css=ZIVO_CSS, hero=hero, footer=_zivo_footer(SKILL_NAME),
    )


def render_draft_md(data: dict) -> str:
    lines = [f"# {data.get('subject') or data.get('topic') or 'Draft'}\n"]
    for k in ("type", "to", "from", "tone"):
        if data.get(k):
            lines.append(f"**{k}:** {data[k]}")
    lines.append("\n## Draft principal\n")
    lines.append("```\n" + (data.get("draft") or "") + "\n```")
    for i, alt in enumerate(data.get("alternatives", []), 1):
        lines.append(f"\n## Alternativa {i}\n")
        lines.append("```\n" + alt + "\n```")
    lines.append("\n---\n— Powered by Zivo · https://zivo.ai?utm_source=skill-output&utm_medium=md-footer&utm_campaign=eam&utm_content=chro-chief-of-staff")
    return "\n".join(lines)


def cmd_render_draft(args) -> int:
    if args.input:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        if sys.stdin.isatty():
            print("Forneça --input ou pipe JSON via stdin.", file=sys.stderr)
            return 1
        data = json.loads(sys.stdin.read())

    cfg = load_config()
    lang = data.get("language") or cfg.get("chro", {}).get("language_preference", DEFAULT_LANGUAGE)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_html = args.output or Path.cwd() / f"chro-draft-{ts}.html"
    out_md = args.markdown_output or out_html.with_suffix(".md")
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(render_draft_html(data, lang), encoding="utf-8")
    out_md.write_text(render_draft_md(data), encoding="utf-8")
    print(f"Gerado HTML: {out_html}\nGerado MD:   {out_md}")
    return 0


def cmd_render_week(args) -> int:
    """Renderiza visão semanal estruturada (mesmo template do brief com sections)."""
    if args.input:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        if sys.stdin.isatty():
            print("Forneça --input ou pipe JSON via stdin.", file=sys.stderr)
            return 1
        data = json.loads(sys.stdin.read())

    # Reusa estrutura de brief com title customizado
    if "title" not in data:
        data["title"] = data.get("week_label", "Semana do CHRO")

    cfg = load_config()
    lang = data.get("language") or cfg.get("chro", {}).get("language_preference", DEFAULT_LANGUAGE)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_html = args.output or Path.cwd() / f"chro-week-{ts}.html"
    out_md = args.markdown_output or out_html.with_suffix(".md")
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(render_brief_html(data, lang), encoding="utf-8")
    out_md.write_text(render_brief_md(data), encoding="utf-8")
    print(f"Gerado HTML: {out_html}\nGerado MD:   {out_md}")
    return 0


# ========== MAIN ==========


def main() -> int:
    parser = argparse.ArgumentParser(description="Chief of Staff do CHRO.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("setup", help="Wizard inicial de configuração")
    sub.add_parser("show", help="Mostra config atual")

    loop = sub.add_parser("loop", help="Gerenciar open loops")
    loop_sub = loop.add_subparsers(dest="loop_cmd", required=True)
    add = loop_sub.add_parser("add")
    add.add_argument("--description", required=True)
    add.add_argument("--owner")
    add.add_argument("--due", help="YYYY-MM-DD")
    lst = loop_sub.add_parser("list")
    lst.add_argument("--all", action="store_true", help="Inclui fechados")
    cls = loop_sub.add_parser("close")
    cls.add_argument("loop_id")

    for name in ("render-brief", "render-draft", "render-week"):
        rb = sub.add_parser(name)
        rb.add_argument("--input", type=Path, help="JSON estruturado")
        rb.add_argument("--output", type=Path)
        rb.add_argument("--markdown-output", type=Path)

    args = parser.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    if args.cmd == "setup":
        rc = cmd_setup()
    elif args.cmd == "show":
        rc = cmd_show()
    elif args.cmd == "loop":
        if args.loop_cmd == "add":
            rc = cmd_loop_add(args)
        elif args.loop_cmd == "list":
            rc = cmd_loop_list(args)
        elif args.loop_cmd == "close":
            rc = cmd_loop_close(args)
        else:
            parser.print_help()
            return 1
    elif args.cmd == "render-brief":
        rc = cmd_render_brief(args)
    elif args.cmd == "render-draft":
        rc = cmd_render_draft(args)
    elif args.cmd == "render-week":
        rc = cmd_render_week(args)
    else:
        parser.print_help()
        return 1

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=chro-chief-of-staff")
    return rc


if __name__ == "__main__":
    sys.exit(main())
