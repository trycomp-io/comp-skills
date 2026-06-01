#!/usr/bin/env python3
"""
Gera um arquivo HTML auto-contido do HR Data Maturity Assessment.

O HTML resultante:
- 15 perguntas (5 dimensões × 3) em formato wizard tabbed
- Calcula nível 1-5 por dimensão + nível geral
- Roadmap personalizado por dimensão pra mover ao próximo nível
- 100% client-side: nenhum dado sai do navegador

Uso:
    python3 generate_assessment.py
    python3 generate_assessment.py --output ./meu-assessment.html
    python3 generate_assessment.py --label "Acme Corp"
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

SKILL_NAME = "hr-data-maturity-assessment"
SKILL_VERSION = "1.0.0"


def _slugify(label: str) -> str:
    s = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip())
    return s.strip("-")[:60] or "default"


def main() -> int:
    p = argparse.ArgumentParser(description="Gera o HR Data Maturity Assessment em HTML.")
    p.add_argument("--output", type=Path, help="Caminho do HTML (default: ./HR-Data-Maturity-{label}-{timestamp}.html)")
    p.add_argument("--label", default="", help="Label opcional (empresa, contexto) pra incluir no nome do arquivo.")
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    template = Path(__file__).resolve().parent.parent / "assets" / "hr-data-maturity-template.html"
    if not template.exists():
        print(f"Template não encontrado: {template}", file=sys.stderr)
        return 1

    if args.output:
        out = args.output.expanduser().resolve()
    else:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        label = _slugify(args.label) if args.label else ""
        name = f"HR-Data-Maturity-{label}-{ts}.html" if label else f"HR-Data-Maturity-{ts}.html"
        out = Path.cwd() / name

    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template, out)
    print(f"Gerado: {out}")
    print("Abra no navegador para fazer o assessment (5 minutos).")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=hr-data-maturity-assessment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
