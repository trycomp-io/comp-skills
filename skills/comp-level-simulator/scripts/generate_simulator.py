#!/usr/bin/env python3
"""
Generate an interactive Comp Level Simulator HTML file in the user's current
working directory. The simulator is a self-contained page (single file) that
the user can open in a browser, share, or host anywhere.

Methodology: 4 pillars (Influence, Autonomy, Complexity, Responsibility),
8 questions, A–E scale, 6 levels (L1–L6). See references/comp-methodology.md.

Usage:
    python3 scripts/generate_simulator.py
    python3 scripts/generate_simulator.py --output /path/to/file.html
    python3 scripts/generate_simulator.py --label "Acme Corp"
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Lead capture / telemetry — best-effort, never blocks the generation.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "comp-level-simulator"
SKILL_VERSION = "1.0.0"


def _slugify(label: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_-]+", "-", label.strip())
    return s.strip("-")[:60] or "default"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Comp Level Simulator HTML file in the current directory."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Path for the generated HTML. Defaults to ./Comp-Level-Simulator-{label}-{timestamp}.html",
    )
    parser.add_argument(
        "--label",
        type=str,
        default="",
        help="Optional label (e.g., company or use-case) to include in the filename.",
    )
    args = parser.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(
                skill_name=SKILL_NAME,
                skill_version=SKILL_VERSION,
                source="github",
            )
        except Exception:
            pass

    template_path = Path(__file__).resolve().parent.parent / "assets" / "comp-level-template.html"
    if not template_path.exists():
        print(f"Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        out_path = args.output.expanduser().resolve()
    else:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        label = _slugify(args.label) if args.label else ""
        name = (
            f"Comp-Level-Simulator-{label}-{ts}.html"
            if label
            else f"Comp-Level-Simulator-{ts}.html"
        )
        out_path = Path.cwd() / name

    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template_path, out_path)

    print(f"Generated: {out_path}")
    print("Open the file in your browser to run the assessment.")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=comp-level-simulator")


if __name__ == "__main__":
    main()
