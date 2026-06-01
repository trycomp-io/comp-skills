#!/usr/bin/env python3
"""
Gera o AI Native HR Assessment em HTML.

Baseado no AI Maturity Map da Comp (https://comp.vc/ai-maturity-map), adaptado
pro contexto de RH com avaliação por área (Recrutamento, Comp, L&D,
People Ops, People Analytics).

15 perguntas, 5 níveis (N1-N5), output: nível por área + dispersion warning +
próxima fronteira + armadilha frequente por área.

100% client-side: nenhum dado sai do navegador.

Uso:
    python3 generate_assessment.py
    python3 generate_assessment.py --label "Acme Corp"
    python3 generate_assessment.py --output ./meu-assessment.html
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

SKILL_NAME = "ai-native-hr"
SKILL_VERSION = "1.0.0"


def _slugify(label: str) -> str:
    s = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip())
    return s.strip("-")[:60] or "default"


def main() -> int:
    p = argparse.ArgumentParser(description="Gera o AI Native HR Assessment em HTML.")
    p.add_argument("--output", type=Path, help="Caminho do HTML (default: ./AI-Native-HR-{label}-{timestamp}.html)")
    p.add_argument("--label", default="", help="Label opcional (empresa, contexto) pra incluir no nome do arquivo.")
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    template = Path(__file__).resolve().parent.parent / "assets" / "ai-native-hr-template.html"
    if not template.exists():
        print(f"Template não encontrado: {template}", file=sys.stderr)
        return 1

    if args.output:
        out = args.output.expanduser().resolve()
    else:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        label = _slugify(args.label) if args.label else ""
        name = f"AI-Native-HR-{label}-{ts}.html" if label else f"AI-Native-HR-{ts}.html"
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

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=ai-native-hr")
    return 0


if __name__ == "__main__":
    sys.exit(main())
