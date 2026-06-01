#!/usr/bin/env python3
"""
paygap_analysis.py — Generate a gender pay-gap HTML report from any HR roster.

Input: a CSV or XLSX with at least these 5 columns (names can vary — the
script auto-detects common aliases, or you can override with flags):
    name | gender | salary | level | area

Output: a self-contained HTML report saved in the current working directory.

Privacy: the report file never phones home; the only network calls are the
optional Comp registration/telemetry endpoints (opt-in, see eam_client.py).

Usage:
    python3 paygap_analysis.py --input employees.csv
    python3 paygap_analysis.py --input employees.xlsx --salary-col salario_bruto
    python3 paygap_analysis.py --input data.csv --output ./paygap-q1.html
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

# Lead capture / telemetry — best-effort, never blocks the analysis.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "paygap-analysis-generator"
SKILL_VERSION = "1.0.0"

# Minimum headcount per gender for a (area, level) group to count toward
# weighted ratios. Standard confidentiality rule in BR pay equity reporting.
MIN_PER_GENDER = 3

NAME_ALIASES = ["name", "nome", "colaborador", "employee", "funcionario", "funcionário"]
GENDER_ALIASES = ["gender", "genero", "gênero", "sexo", "sex"]
SALARY_ALIASES = [
    "salary",
    "salario",
    "salário",
    "salario_base",
    "salário base",
    "salario_bruto",
    "salário bruto",
    "gross_salary",
    "remuneracao",
    "remuneração",
    "monthly_salary",
]
LEVEL_ALIASES = [
    "level",
    "nivel",
    "nível",
    "job_level",
    "cargo_level",
    "senioridade",
    "seniority",
    "grade",
    "agrupamento",
]
AREA_ALIASES = [
    "area",
    "área",
    "departamento",
    "department",
    "funcao",
    "função",
    "diretoria",
    "business_unit",
    "bu",
    "nivel1",
    "nível 1",
]

FEMALE_VALUES = {"f", "female", "feminino", "fem", "mulher"}
MALE_VALUES = {"m", "male", "masculino", "masc", "homem"}


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def _normalize_key(s: str) -> str:
    return _strip_accents(s).strip().lower().replace(" ", "_")


def auto_detect_column(headers: list[str], candidates: list[str]) -> str | None:
    normalized = {_normalize_key(h): h for h in headers}
    for cand in candidates:
        key = _normalize_key(cand)
        if key in normalized:
            return normalized[key]
    return None


def load_rows(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    ext = path.suffix.lower()
    if ext == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            rows = list(reader)
        return headers, rows
    if ext in (".xlsx", ".xlsm"):
        try:
            import openpyxl  # type: ignore
        except ImportError:
            sys.exit(
                "Excel input requires openpyxl. Install it with:\n"
                "    pip install openpyxl\n"
                "Or convert your file to CSV and rerun."
            )
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(h) if h is not None else "" for h in next(rows_iter)]
        rows = []
        for row in rows_iter:
            rows.append({headers[i]: row[i] for i in range(len(headers))})
        return headers, rows
    sys.exit(f"Unsupported file extension: {ext}. Use .csv or .xlsx.")


def _to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(".", "").replace(",", ".")
    # Try without thousands-separator removal too
    for candidate in (s, str(v).strip().replace(",", "")):
        try:
            return float(candidate)
        except ValueError:
            continue
    return None


def _norm_gender(v: Any) -> str | None:
    if v is None:
        return None
    s = _normalize_key(str(v))
    if s in FEMALE_VALUES:
        return "F"
    if s in MALE_VALUES:
        return "M"
    return None


def _slugify(s: str) -> str:
    s = _strip_accents(s).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "unknown"


def analyze(
    rows: list[dict[str, Any]],
    name_col: str,
    gender_col: str,
    salary_col: str,
    level_col: str,
    area_col: str,
) -> dict[str, Any]:
    total = len(rows)
    excluded = 0

    # Per (area, level) bucket
    buckets: dict[tuple[str, str], dict[str, list[float]]] = {}
    for row in rows:
        gender = _norm_gender(row.get(gender_col))
        salary = _to_float(row.get(salary_col))
        level = (row.get(level_col) or "").strip() if row.get(level_col) is not None else ""
        area = (row.get(area_col) or "").strip() if row.get(area_col) is not None else ""

        if not gender or not salary or not level or not area:
            excluded += 1
            continue

        key = (area, level)
        bucket = buckets.setdefault(key, {"F": [], "M": []})
        bucket[gender].append(salary)

    # Aggregate per area
    areas: list[dict[str, Any]] = []
    global_weighted_sum = 0.0
    global_weighted_hc = 0

    area_to_buckets: dict[str, list[tuple[str, dict[str, list[float]]]]] = {}
    for (area, level), bucket in buckets.items():
        area_to_buckets.setdefault(area, []).append((level, bucket))

    for area_name in sorted(area_to_buckets.keys()):
        groups = []
        area_weighted_sum = 0.0
        area_weighted_hc = 0
        area_total_hc = 0

        for level, bucket in sorted(area_to_buckets[area_name], key=lambda x: x[0]):
            hc_f = len(bucket["F"])
            hc_m = len(bucket["M"])
            total_hc = hc_f + hc_m
            area_total_hc += total_hc
            is_valid = hc_f >= MIN_PER_GENDER and hc_m >= MIN_PER_GENDER

            entry = {
                "name": level,
                "hcF": hc_f,
                "hcM": hc_m,
                "medF": None,
                "medM": None,
                "ratio": None,
                "isValid": is_valid,
            }

            if is_valid:
                med_f = statistics.median(bucket["F"])
                med_m = statistics.median(bucket["M"])
                ratio = (med_f / med_m) * 100 if med_m > 0 else None
                entry["medF"] = round(med_f, 2)
                entry["medM"] = round(med_m, 2)
                entry["ratio"] = round(ratio, 2) if ratio is not None else None
                if ratio is not None:
                    area_weighted_sum += ratio * total_hc
                    area_weighted_hc += total_hc

            groups.append(entry)

        weighted_ratio = (
            (area_weighted_sum / area_weighted_hc) if area_weighted_hc > 0 else None
        )
        gap = (weighted_ratio - 100) if weighted_ratio is not None else None

        if weighted_ratio is not None and area_weighted_hc > 0:
            global_weighted_sum += weighted_ratio * area_weighted_hc
            global_weighted_hc += area_weighted_hc

        areas.append(
            {
                "name": area_name,
                "slug": _slugify(area_name),
                "weightedRatio": round(weighted_ratio, 2) if weighted_ratio else None,
                "gap": round(gap, 2) if gap is not None else None,
                "totalHc": area_total_hc,
                "analyzedHc": area_weighted_hc,
                "groups": groups,
            }
        )

    global_weighted_ratio = (
        (global_weighted_sum / global_weighted_hc) if global_weighted_hc > 0 else None
    )
    global_gap = (global_weighted_ratio - 100) if global_weighted_ratio is not None else None

    insights = []
    insights.append(
        f"Total de {total - excluded} colaboradores analisados de {total} no roster"
        + (f" ({excluded} excluído(s) por dados incompletos)." if excluded else ".")
    )
    if global_weighted_ratio is not None:
        insights.append(
            f"Razão ponderada global: {global_weighted_ratio:.2f}% "
            f"(mulheres ganham {abs(global_gap):.2f}% "
            f"{'menos' if global_gap < 0 else 'mais'} que homens na mediana ponderada)."
        )
    insights.append(
        "Regra de confidencialidade aplicada: grupos (área × nível) com menos de 3 pessoas "
        "de cada gênero foram excluídos do cálculo de razão ponderada."
    )

    return {
        "meta": {
            "globalWeightedRatio": round(global_weighted_ratio, 2) if global_weighted_ratio else 0,
            "globalGap": round(global_gap, 2) if global_gap else 0,
            "totalEmployees": total,
            "totalAnalyzedEmployees": total - excluded,
            "excludedEmployees": excluded,
        },
        "areas": areas,
        "insights": insights,
    }


def render_html(report: dict[str, Any], template_path: Path, output_path: Path) -> None:
    template = template_path.read_text(encoding="utf-8")
    # Escape `</` to `<\/` so area/level names containing a literal `</script>`
    # cannot break out of the inline <script> block (XSS via injected payload).
    # JSON parsers treat the escaped form identically.
    payload = json.dumps(report, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("__REPORT_DATA__", payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gender pay-gap HTML report generator (CSV/XLSX in → HTML out)."
    )
    parser.add_argument("--input", type=Path, required=True, help="Input CSV or XLSX")
    parser.add_argument("--output", type=Path, help="Output HTML path (default: ./paygap-{timestamp}.html)")
    parser.add_argument("--name-col", help="Name column override")
    parser.add_argument("--gender-col", help="Gender column override")
    parser.add_argument("--salary-col", help="Salary column override")
    parser.add_argument("--level-col", help="Level column override")
    parser.add_argument("--area-col", help="Area column override")
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

    headers, rows = load_rows(args.input)
    if not rows:
        sys.exit("Input file is empty.")

    name_col = args.name_col or auto_detect_column(headers, NAME_ALIASES)
    gender_col = args.gender_col or auto_detect_column(headers, GENDER_ALIASES)
    salary_col = args.salary_col or auto_detect_column(headers, SALARY_ALIASES)
    level_col = args.level_col or auto_detect_column(headers, LEVEL_ALIASES)
    area_col = args.area_col or auto_detect_column(headers, AREA_ALIASES)

    missing = []
    if not gender_col:
        missing.append(f"gender (tried: {', '.join(GENDER_ALIASES[:4])} — pass --gender-col)")
    if not salary_col:
        missing.append(f"salary (tried: {', '.join(SALARY_ALIASES[:4])} — pass --salary-col)")
    if not level_col:
        missing.append(f"level (tried: {', '.join(LEVEL_ALIASES[:4])} — pass --level-col)")
    if not area_col:
        missing.append(f"area (tried: {', '.join(AREA_ALIASES[:4])} — pass --area-col)")
    if missing:
        sys.exit("Could not detect required columns:\n  - " + "\n  - ".join(missing))

    print(
        f"Columns: gender={gender_col!r}  salary={salary_col!r}  "
        f"level={level_col!r}  area={area_col!r}"
    )
    if name_col:
        print(f"Name column (informational): {name_col!r}")
    print(f"Rows: {len(rows)}")

    report = analyze(
        rows,
        name_col=name_col or "",
        gender_col=gender_col,
        salary_col=salary_col,
        level_col=level_col,
        area_col=area_col,
    )

    template_path = Path(__file__).resolve().parent.parent / "assets" / "paygap-template.html"
    output_path = (
        args.output
        if args.output
        else Path.cwd() / f"paygap-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    )
    render_html(report, template_path, output_path)

    meta = report["meta"]
    print(f"Generated: {output_path}")
    print(
        f"  total={meta['totalEmployees']} analyzed={meta['totalAnalyzedEmployees']} "
        f"excluded={meta['excludedEmployees']}"
    )
    print(
        f"  global weighted ratio: {meta['globalWeightedRatio']:.2f}% "
        f"(gap: {meta['globalGap']:.2f}%)"
    )

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=paygap-analysis-generator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
