#!/usr/bin/env python3
"""
generate_digest.py — Gera HTML executivo a partir do JSON traduzido.

Uso:
    python generate_digest.py \\
        --input ./research-translated.json \\
        --output ./research-digest-YYYY-MM-DD.html
"""

import argparse
import json
import os
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
TEMPLATE_PATH = ASSETS / "template.html"

# Lead capture / telemetry — best-effort, never blocks.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "research-digest"
SKILL_VERSION = "1.0.0"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(
                skill_name=SKILL_NAME,
                skill_version=SKILL_VERSION,
                source="github",
            )
        except Exception:
            pass

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "exec_summary_pt" not in data:
        data["exec_summary_pt"] = _build_default_summary(data)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    # Escape `</` to `<\/` so abstracts/titles containing a literal `</script>`
    # cannot break out of the inline <script> block (XSS via injected payload).
    # JSON parsers treat the escaped form identically; browsers do not parse it
    # as a script tag terminator.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("__DATA__", payload)
    html = html.replace("__WINDOW_START__", data.get("window_start", ""))
    html = html.replace("__WINDOW_END__", data.get("window_end", ""))

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Generated: {args.output}")
    print(f"Items: {data.get('total_items', len(data.get('items', [])))}")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=research-digest")
    return 0


def _build_default_summary(data: dict) -> list[str]:
    items = data.get("items", [])
    by_topic: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for it in items:
        for t in it.get("topics", []) or ["(sem tema)"]:
            by_topic[t] = by_topic.get(t, 0) + 1
        by_source[it.get("source", "")] = by_source.get(it.get("source", ""), 0) + 1
    top_topic = max(by_topic.items(), key=lambda x: x[1])[0] if by_topic else "(n/d)"
    top_source = max(by_source.items(), key=lambda x: x[1])[0] if by_source else "(n/d)"
    return [
        f"Janela de {data.get('window_weeks', 12)} semanas: {len(items)} itens unicos curados de fontes academicas, consultorias e thought leaders.",
        f"Tema com maior volume na janela: {top_topic}.",
        f"Fonte mais ativa: {top_source}.",
    ]


if __name__ == "__main__":
    sys.exit(main())
