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

Config persistido em ~/.comp-skills/chro-context.json.

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

CONFIG_DIR = Path.home() / ".comp-skills"
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
    print("Estamos usando defaults. Customize editando ~/.comp-skills/chro-context.json depois se quiser.")

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
<meta charset="UTF-8"><title>{title}</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  body{{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b;line-height:1.6}}
  .doc{{max-width:780px;background:white;border-radius:12px;padding:3rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin:2rem auto}}
  h1{{font-size:2rem;font-weight:800;color:#0f172a;margin-bottom:.5rem}}
  h2{{font-size:1.15rem;font-weight:700;color:#0f172a;margin-top:1.75rem;margin-bottom:.75rem;padding-bottom:.4rem;border-bottom:2px solid #f1f5f9}}
  .meta{{font-size:.875rem;color:#64748b;border-left:3px solid #ff4456;padding-left:1rem;margin-bottom:2rem}}
  ul{{list-style:disc;padding-left:1.5rem}}
  li{{padding:.2rem 0}}
  .talking-point{{background:#fef3c7;border-left:4px solid #f59e0b;padding:.75rem 1rem;border-radius:0 8px 8px 0;margin-bottom:.5rem}}
  .ask{{background:#dbeafe;border-left:4px solid #3b82f6;padding:.75rem 1rem;border-radius:0 8px 8px 0;margin-bottom:.5rem}}
  .pill{{display:inline-block;padding:.15rem .55rem;border-radius:999px;font-size:.7rem;font-weight:600;background:#fee2e2;color:#991b1b}}
</style></head>
<body>
<div class="doc">
<h1>{title}</h1>
<div class="meta">{meta}</div>
{body}
</div>
<footer style="text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;padding:1rem;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=chro-chief-of-staff" style="color:#ff4456;font-weight:600;text-decoration:none;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</body></html>
"""


def _section(title: str, items, kind: str = "list") -> str:
    if not items:
        return ""
    if kind == "list":
        body = "<ul>" + "".join(f"<li>{_esc(i)}</li>" for i in items) + "</ul>"
    elif kind == "talking-points":
        body = "".join(f'<div class="talking-point">{_esc(i)}</div>' for i in items)
    elif kind == "asks":
        body = "".join(f'<div class="ask">{_esc(i)}</div>' for i in items)
    else:
        body = "<p>" + _esc(items) + "</p>"
    return f"<h2>{_esc(title)}</h2>{body}"


def render_brief_html(data: dict, lang: str) -> str:
    title = data.get("title", "Pre-meeting Brief")
    meta_parts = []
    for k in ("meeting", "date", "participants"):
        if data.get(k):
            v = data[k]
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            meta_parts.append(f"<strong>{k}:</strong> {_esc(v)}")
    meta = "<br>".join(meta_parts)

    body = []
    sections = data.get("sections", [])
    for sec in sections:
        sec_title = sec.get("title", "")
        kind = sec.get("kind", "list")
        items = sec.get("items", [])
        body.append(_section(sec_title, items, kind))

    return BRIEF_HTML.format(lang=lang, title=_esc(title), meta=meta, body="\n".join(body))


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
    lines.append("\n---\n— Powered by Comp · https://comp.vc?utm_source=skill-output&utm_medium=md-footer&utm_campaign=eam&utm_content=chro-chief-of-staff")
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
<meta charset="UTF-8"><title>{title}</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  body{{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b;line-height:1.6}}
  .doc{{max-width:680px;background:white;border-radius:12px;padding:2.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin:2rem auto}}
  h1{{font-size:1.5rem;font-weight:800;color:#0f172a;margin-bottom:.5rem}}
  .meta{{font-size:.875rem;color:#64748b;border-left:3px solid #ff4456;padding-left:1rem;margin-bottom:1.5rem}}
  .draft{{background:#fafbfc;border:1px solid #e2e8f0;border-radius:8px;padding:1.5rem;white-space:pre-wrap;font-size:1rem;line-height:1.65}}
  .alt{{margin-top:1.5rem;padding-top:1rem;border-top:1px dashed #cbd5e0}}
  .alt-label{{font-size:.7rem;font-weight:700;text-transform:uppercase;color:#94a3b8;letter-spacing:.05em;margin-bottom:.5rem}}
</style></head>
<body>
<div class="doc">
<h1>{title}</h1>
<div class="meta">{meta}</div>
{body}
</div>
<footer style="text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;padding:1rem;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=chro-chief-of-staff" style="color:#ff4456;font-weight:600;text-decoration:none;">Comp</a>
</footer>
</body></html>
"""


def render_draft_html(data: dict, lang: str) -> str:
    title = data.get("subject") or data.get("topic") or "Draft"
    meta_parts = []
    for k in ("type", "to", "from", "tone"):
        if data.get(k):
            meta_parts.append(f"<strong>{k}:</strong> {_esc(data[k])}")
    meta = "<br>".join(meta_parts)

    body = []
    primary = data.get("draft", "")
    body.append(f'<div class="draft">{_esc(primary)}</div>')

    for i, alt in enumerate(data.get("alternatives", []), 1):
        body.append(f'<div class="alt"><div class="alt-label">Alternativa {i}</div><div class="draft">{_esc(alt)}</div></div>')

    return DRAFT_HTML.format(lang=lang, title=_esc(title), meta=meta, body="\n".join(body))


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
    lines.append("\n---\n— Powered by Comp · https://comp.vc?utm_source=skill-output&utm_medium=md-footer&utm_campaign=eam&utm_content=chro-chief-of-staff")
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

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=chro-chief-of-staff")
    return rc


if __name__ == "__main__":
    sys.exit(main())
