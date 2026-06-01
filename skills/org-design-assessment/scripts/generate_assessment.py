#!/usr/bin/env python3
"""
Gera o Org Design Maturity Assessment em HTML.
Framework Comp (4 pilares × 3 perguntas) — Score 0-100.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "org-design-assessment"
SKILL_VERSION = "1.0.0"


def _slug(label: str) -> str:
    s = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip()).strip("-")[:60] or "default"


def main() -> int:
    p = argparse.ArgumentParser(description="Gera Org Design Maturity Assessment em HTML.")
    p.add_argument("--output", type=Path)
    p.add_argument("--label", default="")
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    template = Path(__file__).resolve().parent.parent / "assets" / "org-design-template.html"
    if not template.exists():
        print(f"Template não encontrado: {template}", file=sys.stderr); return 1

    if args.output:
        out = args.output.expanduser().resolve()
    else:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        label = _slug(args.label) if args.label else ""
        name = f"Org-Design-{label}-{ts}.html" if label else f"Org-Design-{ts}.html"
        out = Path.cwd() / name

    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template, out)
    print(f"Gerado: {out}")
    print("Abra no navegador para fazer o assessment (~5 minutos).")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=org-design-assessment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
