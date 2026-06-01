#!/usr/bin/env python3
"""
reajuste_impact.py — Calcula o impacto financeiro de um reajuste salarial
(dissídio, mérito, ajuste pontual) na folha total.

Lê CSV/XLSX de roster + regra de reajuste (flat %, por nível, ou por área)
e devolve:
- Aumento total mensal e anual (incluindo encargos)
- % de impacto na folha
- Breakdown por nível/área
- Custo por colaborador

Inclui encargos patronais (~35.8%) — o reajuste não é só salário.

Uso:
    # Flat 5% pra todo mundo
    python3 reajuste_impact.py --input roster.csv --flat 5

    # Diferenciado por nível
    python3 reajuste_impact.py --input roster.csv --rule-by level \\
        --rules '{"Junior":7,"Pleno":5,"Senior":4,"Manager":3}'

    # Diferenciado por área
    python3 reajuste_impact.py --input roster.csv --rule-by area \\
        --rules '{"Eng":5,"Sales":4,"Backoffice":3}'
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "reajuste-impact-calculator"
SKILL_VERSION = "1.0.0"

ENCARGOS_RATE = 0.358  # INSS 20 + FGTS 8 + SAT 2 + Sistema S 5.8
PROVISOES_RATE = 0.197  # 13º + férias + 1/3 + multa FGTS provisão
FULL_LOAD = ENCARGOS_RATE + PROVISOES_RATE  # ~55.5%


ALIASES = {
    "name":   ["name", "nome", "colaborador"],
    "salary": ["salary", "salario", "salário", "salario_base", "gross_salary"],
    "area":   ["area", "área", "departamento", "department"],
    "level":  ["level", "nivel", "nível", "senioridade", "grade"],
}


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").strip().lower().replace(" ", "_")


def auto_detect(headers: list[str], key: str) -> str | None:
    h = {_norm(x): x for x in headers}
    for cand in ALIASES[key]:
        if _norm(cand) in h:
            return h[_norm(cand)]
    return None


def _to_float(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def load_csv(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def load_xlsx(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    try:
        import openpyxl  # type: ignore
    except ImportError:
        sys.exit("Excel requer openpyxl. pip install openpyxl")
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    headers = [str(h) if h is not None else "" for h in next(it)]
    rows = [{headers[i]: r[i] for i in range(len(headers))} for r in it]
    return headers, rows


def get_pct(row: dict, cols: dict, rule_by: str, rules: dict[str, float], flat: float | None) -> float:
    if flat is not None:
        return flat
    if rule_by in ("area", "level"):
        key = str(row.get(cols.get(rule_by, "")) or "").strip()
        return rules.get(key, 0.0)
    return 0.0


def analyze(rows: list[dict], cols: dict, rule_by: str, rules: dict[str, float], flat: float | None) -> dict:
    by_group: dict[str, dict[str, float]] = defaultdict(lambda: {"hc": 0, "salary_before": 0.0, "salary_after": 0.0, "pct": 0.0})
    total_before = 0.0
    total_after = 0.0
    employee_summary = []

    for row in rows:
        salary = _to_float(row.get(cols["salary"]))
        if salary <= 0:
            continue
        pct = get_pct(row, cols, rule_by, rules, flat)
        increase = salary * pct / 100
        new_salary = salary + increase
        total_before += salary
        total_after += new_salary

        if rule_by == "level":
            group_key = str(row.get(cols.get("level") or "") or "—").strip() or "—"
        elif rule_by == "area":
            group_key = str(row.get(cols.get("area") or "") or "—").strip() or "—"
        else:
            group_key = "Todos"

        by_group[group_key]["hc"] += 1  # type: ignore
        by_group[group_key]["salary_before"] += salary
        by_group[group_key]["salary_after"] += new_salary
        by_group[group_key]["pct"] = pct
        employee_summary.append({
            "name": str(row.get(cols.get("name") or "") or "").strip(),
            "salary_before": salary,
            "salary_after": round(new_salary, 2),
            "increase": round(increase, 2),
            "pct": pct,
        })

    delta_salary = total_after - total_before
    delta_with_load = delta_salary * (1 + FULL_LOAD)

    group_rows = sorted([
        {
            "group": g, "hc": v["hc"], "pct": v["pct"],
            "salary_before": round(v["salary_before"], 2),
            "salary_after": round(v["salary_after"], 2),
            "delta_salary": round(v["salary_after"] - v["salary_before"], 2),
            "delta_with_load": round((v["salary_after"] - v["salary_before"]) * (1 + FULL_LOAD), 2),
        }
        for g, v in by_group.items()
    ], key=lambda x: x["delta_with_load"], reverse=True)

    return {
        "headcount": sum(int(v["hc"]) for v in by_group.values()),
        "rule": {"by": rule_by, "flat": flat, "rules": rules},
        "salary_before_total": round(total_before, 2),
        "salary_after_total": round(total_after, 2),
        "delta_salary_monthly": round(delta_salary, 2),
        "delta_with_load_monthly": round(delta_with_load, 2),
        "delta_with_load_annual": round(delta_with_load * 12, 2),
        "pct_impact_on_payroll": round((delta_salary / total_before) * 100, 2) if total_before > 0 else 0,
        "by_group": group_rows,
        "top_increases": sorted(employee_summary, key=lambda e: e["increase"], reverse=True)[:10],
    }


def fmt(v: float) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def print_result(r: dict) -> None:
    print()
    print("=" * 64)
    print("  IMPACTO DE REAJUSTE")
    print("=" * 64)
    rule = r["rule"]
    if rule["flat"] is not None:
        print(f"  Regra:                  Flat {rule['flat']}% pra todos")
    else:
        print(f"  Regra:                  Diferenciado por {rule['by']}")
        for k, v in rule["rules"].items():
            print(f"    - {k}: {v}%")
    print(f"  Headcount:              {r['headcount']}")
    print()
    print(f"  Folha antes (salários): {fmt(r['salary_before_total'])}")
    print(f"  Folha depois:           {fmt(r['salary_after_total'])}")
    print(f"  ∆ salários mensal:      {fmt(r['delta_salary_monthly'])} ({r['pct_impact_on_payroll']:.2f}%)")
    print(f"  ∆ com encargos +55.5%:  {fmt(r['delta_with_load_monthly'])} /mês")
    print(f"  ∆ anual com encargos:   {fmt(r['delta_with_load_annual'])} /ano")
    print()
    print("  POR GRUPO")
    print("  " + "-" * 56)
    print(f"  {'Grupo':<22} {'HC':>4} {'%':>5} {'∆ mensal (load)':>16}")
    for g in r["by_group"]:
        print(f"  {g['group'][:22]:<22} {g['hc']:>4} {g['pct']:>5}% {fmt(g['delta_with_load']):>16}")
    print()


def main() -> int:
    p = argparse.ArgumentParser(description="Calcula impacto financeiro de reajuste salarial (Brasil).")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--flat", type=float, help="%% flat pra todo mundo")
    p.add_argument("--rule-by", choices=["level", "area"], help="Diferenciado por nível ou área")
    p.add_argument("--rules", help="JSON com regras (ex: '{\"Junior\":7,\"Senior\":4}')")
    p.add_argument("--salary-col"); p.add_argument("--area-col"); p.add_argument("--level-col"); p.add_argument("--name-col")
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    if args.flat is None and not (args.rule_by and args.rules):
        sys.exit("Use --flat <%> OU --rule-by <level|area> + --rules <json>")
    rules = json.loads(args.rules) if args.rules else {}

    ext = args.input.suffix.lower()
    if ext == ".csv":
        headers, rows = load_csv(args.input)
    elif ext in (".xlsx", ".xlsm"):
        headers, rows = load_xlsx(args.input)
    else:
        sys.exit(f"Formato não suportado: {ext}")

    cols = {k: getattr(args, f"{k}_col", None) or auto_detect(headers, k) for k in ALIASES}
    if not cols.get("salary"):
        sys.exit("Coluna de salário não detectada. Use --salary-col.")

    r = analyze(rows, cols, args.rule_by or "all", rules, args.flat)
    print_result(r)

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=reajuste-impact-calculator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
