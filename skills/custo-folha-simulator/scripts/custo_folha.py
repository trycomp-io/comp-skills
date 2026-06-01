#!/usr/bin/env python3
"""
custo_folha.py — Simulador de custo de folha de pagamento (Brasil).

Calcula o custo total empregador a partir de salários brutos, incluindo
encargos patronais (INSS, FGTS, SAT, Sistema S), provisões (13º, férias+1/3,
multa FGTS rescisória) e benefícios. NÃO substitui sistema de folha — é
simulação rápida pra orçamento, projeção e cenários.

Dois modos:
  - Detalhado: CSV de colaboradores (mínimo: nome, salário; opcional: benefícios)
  - Estimativa: headcount + salário médio (sem CSV)

Uso:
    # Detalhado
    python3 custo_folha.py --input roster.csv

    # Estimativa
    python3 custo_folha.py --headcount 50 --salario-medio 8000
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

SKILL_NAME = "custo-folha-simulator"
SKILL_VERSION = "1.0.0"


# ========== Encargos patronais (Brasil, ref. 2024/2025) ==========
INSS_PATRONAL = 0.20      # 20% sobre folha
FGTS = 0.08               # 8%
SAT = 0.02                # Seguro Acidente Trabalho — varia 1-3%, default 2%
SISTEMA_S = 0.058         # Salário-educação + INCRA + SENAI/SESI/SEBRAE — varia, ~5.8%
PROVISAO_13 = 1/12        # 8.33%
PROVISAO_FERIAS = 1/12    # 8.33% (apenas o salário) — 1/3 constitucional é adicional
TERCO_FERIAS = (1/12)/3   # 2.78%
PROVISAO_MULTA_FGTS = 0.08 * 0.40 / 12  # ~0.27%/mês (provisão pra multa rescisória futura)

ENCARGOS_RATE = INSS_PATRONAL + FGTS + SAT + SISTEMA_S  # ~35.8%
PROVISOES_RATE = PROVISAO_13 + PROVISAO_FERIAS + TERCO_FERIAS + PROVISAO_MULTA_FGTS  # ~19.7%


# ========== Column detection (modo detalhado) ==========

ALIASES = {
    "name":     ["name", "nome", "colaborador", "employee"],
    "salary":   ["salary", "salario", "salário", "salario_base", "salário base", "gross_salary"],
    "area":     ["area", "área", "departamento", "department"],
    "level":    ["level", "nivel", "nível", "senioridade"],
    "vr_va":    ["vr_va", "vr", "va", "vale_refeicao", "vale_alimentacao"],
    "outros":   ["outros", "outros_beneficios", "beneficios_outros", "extras"],
}


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").strip().lower().replace(" ", "_")


def auto_detect(headers: list[str], key: str) -> str | None:
    norm_h = {_norm(h): h for h in headers}
    for cand in ALIASES[key]:
        if _norm(cand) in norm_h:
            return norm_h[_norm(cand)]
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
        try:
            return float(str(v).strip().replace(",", ""))
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
        sys.exit("Excel input requer openpyxl. pip install openpyxl")
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    headers = [str(h) if h is not None else "" for h in next(it)]
    rows = [{headers[i]: r[i] for i in range(len(headers))} for r in it]
    return headers, rows


# ========== Cálculo ==========


def calculate_employee(salary: float, vr_va: float = 0.0, outros: float = 0.0) -> dict[str, float]:
    encargos = salary * ENCARGOS_RATE
    provisoes = salary * PROVISOES_RATE
    beneficios = vr_va + outros
    custo_total = salary + encargos + provisoes + beneficios
    return {
        "salario": salary,
        "encargos": round(encargos, 2),
        "provisoes": round(provisoes, 2),
        "beneficios": round(beneficios, 2),
        "custo_total": round(custo_total, 2),
    }


def analyze_detailed(rows: list[dict], cols: dict[str, str | None]) -> dict[str, Any]:
    total_salary = 0.0
    total_encargos = 0.0
    total_provisoes = 0.0
    total_beneficios = 0.0
    by_area: dict[str, dict[str, float | int]] = defaultdict(lambda: {"hc": 0, "salary": 0.0, "custo_total": 0.0})

    for row in rows:
        salary = _to_float(row.get(cols["salary"]))
        if salary <= 0:
            continue
        vr = _to_float(row.get(cols["vr_va"])) if cols.get("vr_va") else 0.0
        outros = _to_float(row.get(cols["outros"])) if cols.get("outros") else 0.0
        area = str(row.get(cols["area"]) or "—").strip() if cols.get("area") else "—"

        emp = calculate_employee(salary, vr, outros)
        total_salary += emp["salario"]
        total_encargos += emp["encargos"]
        total_provisoes += emp["provisoes"]
        total_beneficios += emp["beneficios"]

        by_area[area]["hc"] += 1  # type: ignore
        by_area[area]["salary"] += salary
        by_area[area]["custo_total"] += emp["custo_total"]

    by_area_list = sorted([
        {"area": a, "hc": v["hc"], "salary_total": round(v["salary"], 2), "custo_total": round(v["custo_total"], 2),
         "custo_medio_pessoa": round(v["custo_total"] / v["hc"], 2) if v["hc"] else 0}
        for a, v in by_area.items()
    ], key=lambda x: x["custo_total"], reverse=True)

    custo_total_mensal = total_salary + total_encargos + total_provisoes + total_beneficios
    return {
        "mode": "detailed",
        "headcount": sum(v["hc"] for v in by_area.values()),
        "total_salary": round(total_salary, 2),
        "total_encargos": round(total_encargos, 2),
        "total_provisoes": round(total_provisoes, 2),
        "total_beneficios": round(total_beneficios, 2),
        "custo_total_mensal": round(custo_total_mensal, 2),
        "custo_total_anual": round(custo_total_mensal * 12, 2),
        "salary_medio": round(total_salary / sum(v["hc"] for v in by_area.values()), 2) if by_area else 0,
        "by_area": by_area_list,
    }


def analyze_estimate(headcount: int, salario_medio: float, vr_va_medio: float = 0.0, outros_medio: float = 0.0) -> dict[str, Any]:
    salary_total = headcount * salario_medio
    benef_total = headcount * (vr_va_medio + outros_medio)
    encargos = salary_total * ENCARGOS_RATE
    provisoes = salary_total * PROVISOES_RATE
    custo_total_mensal = salary_total + encargos + provisoes + benef_total
    return {
        "mode": "estimate",
        "headcount": headcount,
        "salary_medio": salario_medio,
        "total_salary": round(salary_total, 2),
        "total_encargos": round(encargos, 2),
        "total_provisoes": round(provisoes, 2),
        "total_beneficios": round(benef_total, 2),
        "custo_total_mensal": round(custo_total_mensal, 2),
        "custo_total_anual": round(custo_total_mensal * 12, 2),
        "by_area": [],
    }


# ========== Output ==========


def fmt(v: float) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def print_result(r: dict) -> None:
    print()
    print("=" * 64)
    print(f"  CUSTO DE FOLHA — modo {r['mode'].upper()}")
    print("=" * 64)
    print(f"  Headcount:                 {r['headcount']}")
    if r.get("salary_medio"):
        print(f"  Salário médio:             {fmt(r['salary_medio'])}")
    print()
    print(f"  Salários brutos:           {fmt(r['total_salary'])}")
    print(f"  Encargos patronais (~36%): {fmt(r['total_encargos'])}")
    print(f"  Provisões (~20%):          {fmt(r['total_provisoes'])}")
    if r['total_beneficios'] > 0:
        print(f"  Benefícios (VR/VA + outros): {fmt(r['total_beneficios'])}")
    print(f"  " + "-" * 56)
    print(f"  CUSTO MENSAL TOTAL:        {fmt(r['custo_total_mensal'])}")
    print(f"  CUSTO ANUAL TOTAL:         {fmt(r['custo_total_anual'])}")
    print(f"  Onerated factor:           {round(r['custo_total_mensal'] / r['total_salary'], 2)}x salário")
    print()

    if r.get("by_area"):
        print("  POR ÁREA")
        print("  " + "-" * 56)
        print(f"  {'Área':<24} {'HC':>4} {'Salário Total':>16} {'Custo Total':>16}")
        for a in r["by_area"]:
            print(f"  {a['area'][:24]:<24} {a['hc']:>4} {fmt(a['salary_total']):>16} {fmt(a['custo_total']):>16}")
        print()


# ========== CLI ==========


def main() -> int:
    p = argparse.ArgumentParser(description="Simulador de custo de folha (Brasil).")
    p.add_argument("--input", type=Path, help="CSV/XLSX de roster (modo detalhado)")
    p.add_argument("--headcount", type=int, help="Headcount agregado (modo estimativa)")
    p.add_argument("--salario-medio", type=float, help="Salário médio (modo estimativa)")
    p.add_argument("--vr-va-medio", type=float, default=0, help="VR/VA médio mensal por pessoa")
    p.add_argument("--outros-medio", type=float, default=0, help="Outros benefícios médios mensais por pessoa")
    p.add_argument("--name-col"); p.add_argument("--salary-col"); p.add_argument("--area-col")
    p.add_argument("--vr-va-col"); p.add_argument("--outros-col")
    p.add_argument("--output-json", type=Path, help="Salva resultado em JSON")
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    if args.input:
        ext = args.input.suffix.lower()
        if ext == ".csv":
            headers, rows = load_csv(args.input)
        elif ext in (".xlsx", ".xlsm"):
            headers, rows = load_xlsx(args.input)
        else:
            sys.exit(f"Formato não suportado: {ext}")
        cols = {k: getattr(args, f"{k.replace('_','_')}_col", None) or auto_detect(headers, k) for k in ALIASES}
        if not cols.get("salary"):
            sys.exit("Coluna de salário não detectada. Use --salary-col.")
        print(f"Colunas: salary={cols['salary']!r} area={cols.get('area')!r} vr={cols.get('vr_va')!r}")
        print(f"Rows: {len(rows)}")
        r = analyze_detailed(rows, cols)
    elif args.headcount and args.salario_medio:
        r = analyze_estimate(args.headcount, args.salario_medio, args.vr_va_medio, args.outros_medio)
    else:
        sys.exit("Forneça --input <csv> ou --headcount + --salario-medio.")

    print_result(r)

    if args.output_json:
        args.output_json.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON salvo em: {args.output_json}")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=custo-folha-simulator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
