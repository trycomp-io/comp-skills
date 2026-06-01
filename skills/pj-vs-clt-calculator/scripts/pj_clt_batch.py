#!/usr/bin/env python3
"""
Batch PJ→CLT equivalence — processes a CSV of PJ offers and outputs CLT-equivalent
gross salaries for each. Useful for HR/People teams standardizing offer policies
across multiple candidates or comparing several PJ contractors at once.

Input CSV columns (required marked *):
    pj_billing*           monthly PJ billing (R$)
    pj_aliquota*          PJ tax rate (e.g., 6 for 6%)
    candidate_name        optional label
    pj_invoices           12 or 13 (default: 12)
    pj_accounting         monthly accounting cost (default: 0)
    clt_vavr_desired      desired monthly VR/VA (default: 0)
    clt_bonus_desired     desired annual bonus (default: 0)
    include_fgts          1/0 — include FGTS in equivalence (default: 1)

Usage:
    python3 pj_clt_batch.py --input offers.csv --output offers_equivalent.csv
"""

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pj_clt_calculator import calculate_pj_to_clt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "pj-vs-clt-calculator"
SKILL_VERSION = "1.0.0"

OUTPUT_FIELDS = [
    "candidate_name",
    "pj_billing",
    "pj_aliquota",
    "pj_invoices",
    "clt_vavr_desired",
    "clt_bonus_desired",
    "clt_equivalent_gross_monthly",
    "clt_equivalent_net_monthly",
    "clt_equivalent_value_annual",
    "difference_brl",
    "status",
]


def _f(row: dict, key: str, default: float = 0.0) -> float:
    val = row.get(key, "")
    if val is None or str(val).strip() == "":
        return default
    return float(val)


def _i(row: dict, key: str, default: int) -> int:
    val = row.get(key, "")
    if val is None or str(val).strip() == "":
        return default
    return int(float(val))


def process_row(row: dict) -> dict:
    try:
        billing = _f(row, "pj_billing")
        aliquota = _f(row, "pj_aliquota")
        if billing <= 0 or aliquota <= 0:
            return {"status": "skipped: missing pj_billing or pj_aliquota"}

        invoices = _i(row, "pj_invoices", 12)
        if invoices not in (12, 13):
            invoices = 12

        include_fgts = _i(row, "include_fgts", 1) == 1

        result = calculate_pj_to_clt(
            pj_billing=billing,
            pj_aliquota=aliquota,
            pj_invoices=invoices,
            pj_accounting=_f(row, "pj_accounting"),
            pj_other_costs=_f(row, "pj_other_costs"),
            clt_vavr_desired=_f(row, "clt_vavr_desired"),
            clt_bonus_desired=_f(row, "clt_bonus_desired"),
            clt_other_benefits_desired=_f(row, "clt_other_benefits_desired"),
            include_fgts=include_fgts,
        )
        return {
            "candidate_name": row.get("candidate_name", ""),
            "pj_billing": billing,
            "pj_aliquota": aliquota,
            "pj_invoices": invoices,
            "clt_vavr_desired": _f(row, "clt_vavr_desired"),
            "clt_bonus_desired": _f(row, "clt_bonus_desired"),
            "clt_equivalent_gross_monthly": result["suggested_clt_gross_monthly"],
            "clt_equivalent_net_monthly": result["clt_components"]["net_monthly"],
            "clt_equivalent_value_annual": result["clt_equivalent_value"],
            "difference_brl": result["equivalence_diff"],
            "status": "ok",
        }
    except Exception as exc:
        return {
            "candidate_name": row.get("candidate_name", ""),
            "status": f"error: {exc}",
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch PJ→CLT equivalence from CSV")
    parser.add_argument("--input", required=True, help="Path to input CSV")
    parser.add_argument("--output", required=True, help="Path for output CSV")
    args = parser.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(
                skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github"
            )
        except Exception:
            pass

    rows_out = []
    with open(args.input, newline="", encoding="utf-8") as fin:
        reader = csv.DictReader(fin)
        for row in reader:
            rows_out.append(process_row(row))

    with open(args.output, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in rows_out:
            writer.writerow(r)

    ok = sum(1 for r in rows_out if r.get("status") == "ok")
    failed = len(rows_out) - ok
    print(f"Processed {len(rows_out)} rows — {ok} ok, {failed} failed/skipped.")
    print(f"Output: {args.output}")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=pj-vs-clt-calculator")


if __name__ == "__main__":
    main()
