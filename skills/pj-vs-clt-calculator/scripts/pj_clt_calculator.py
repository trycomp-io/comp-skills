#!/usr/bin/env python3
"""
PJ vs CLT Calculator
Calculates salary equivalence between Brazilian CLT and PJ contracts.

Usage:
    python3 pj_clt_calculator.py --direction clt-to-pj --clt-salary 10000 --pj-aliquota 6
    python3 pj_clt_calculator.py --direction pj-to-clt --pj-billing 15000 --pj-aliquota 6
"""

import sys
import argparse
from pathlib import Path

# Lead capture / telemetry — best-effort, never blocks the calc.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "pj-vs-clt-calculator"
SKILL_VERSION = "1.0.0"


# ========== TAX TABLES (2024/2025) ==========

INSS_TABLE = [
    {"limit": 1412.00, "rate": 0.075, "deduction": 0.00},
    {"limit": 2666.68, "rate": 0.09, "deduction": 21.18},
    {"limit": 4000.03, "rate": 0.12, "deduction": 101.18},
    {"limit": 7786.02, "rate": 0.14, "deduction": 181.18}
]
INSS_CEILING = 7786.02
INSS_MAX_CONTRIBUTION = 908.85

IRPF_TABLE = [
    {"limit": 2259.20, "rate": 0, "deduction": 0.00},
    {"limit": 2826.65, "rate": 0.075, "deduction": 169.44},
    {"limit": 3751.05, "rate": 0.15, "deduction": 381.44},
    {"limit": 4664.68, "rate": 0.225, "deduction": 662.77},
    {"limit": float('inf'), "rate": 0.275, "deduction": 896.00}
]

FACTOR_13_33 = 13 + (1/3)  # 13.333... (12 months + 13th + 1/3 vacation)
FGTS_RATE = 0.08  # 8%


# ========== CALCULATION FUNCTIONS ==========

def calculate_inss(gross_salary):
    """
    Calculate progressive INSS contribution.

    Args:
        gross_salary (float): Gross monthly salary

    Returns:
        float: INSS contribution amount (rounded to 2 decimals)
    """
    if gross_salary > INSS_CEILING:
        return round(INSS_MAX_CONTRIBUTION, 2)

    for bracket in INSS_TABLE:
        if gross_salary <= bracket["limit"]:
            inss = (gross_salary * bracket["rate"]) - bracket["deduction"]
            return round(inss, 2)

    # Fallback (should not reach here if table is correct)
    inss = (gross_salary * 0.14) - 181.18
    return round(inss, 2)


def calculate_irpf(gross_salary, inss_contribution):
    """
    Calculate progressive IRPF (Income Tax).

    Args:
        gross_salary (float): Gross monthly salary
        inss_contribution (float): INSS amount already calculated

    Returns:
        float: IRPF amount (rounded to 2 decimals)
    """
    taxable_base = gross_salary - inss_contribution

    for bracket in IRPF_TABLE:
        if taxable_base <= bracket["limit"]:
            irpf = (taxable_base * bracket["rate"]) - bracket["deduction"]
            return round(max(0, irpf), 2)

    # Fallback for highest bracket
    irpf = (taxable_base * 0.275) - 896.00
    return round(max(0, irpf), 2)


def calculate_clt_net_salary(gross_salary):
    """
    Calculate CLT net monthly salary after INSS and IRPF.

    Args:
        gross_salary (float): Gross monthly salary

    Returns:
        float: Net monthly salary (rounded to 2 decimals)
    """
    inss = calculate_inss(gross_salary)
    irpf = calculate_irpf(gross_salary, inss)
    net = gross_salary - inss - irpf
    return round(net, 2)


def get_clt_annual_components(gross_salary, annual_vavr=0, annual_bonus=0, annual_other_benefits=0):
    """
    Calculate all CLT annual compensation components.

    Args:
        gross_salary (float): Gross monthly salary
        annual_vavr (float): Total annual meal vouchers/food allowance
        annual_bonus (float): Total annual net bonus
        annual_other_benefits (float): Total annual other benefits

    Returns:
        dict: Dictionary with net_monthly, net_annualized_salary, annual_benefits,
              total_net_income, annual_fgts
    """
    if gross_salary <= 0:
        return {
            "net_monthly": 0,
            "net_annualized_salary": 0,
            "annual_benefits": annual_vavr + annual_bonus + annual_other_benefits,
            "total_net_income": annual_vavr + annual_bonus + annual_other_benefits,
            "annual_fgts": 0
        }

    net_monthly = calculate_clt_net_salary(gross_salary)
    net_annualized_salary = round(net_monthly * FACTOR_13_33, 2)
    annual_benefits = annual_vavr + annual_bonus + annual_other_benefits
    total_net_income = round(net_annualized_salary + annual_benefits, 2)
    annual_fgts = round(gross_salary * FACTOR_13_33 * FGTS_RATE, 2)

    return {
        "net_monthly": net_monthly,
        "net_annualized_salary": net_annualized_salary,
        "annual_benefits": annual_benefits,
        "total_net_income": total_net_income,
        "annual_fgts": annual_fgts
    }


# ========== EQUIVALENCE CALCULATIONS ==========

def calculate_clt_to_pj(clt_salary, pj_aliquota, clt_vavr=0, clt_bonus_annual=0,
                       clt_other_benefits=0, pj_invoices=12, pj_accounting=0,
                       pj_other_costs=0, include_fgts=True):
    """
    Calculate required PJ billing to match CLT compensation.
    Uses direct formula: required_pj_annual_gross = (clt_target + costs) / (1 - aliquota)

    Args:
        clt_salary (float): CLT gross monthly salary
        pj_aliquota (float): PJ tax rate (percentage, e.g., 6 for 6%)
        clt_vavr (float): CLT monthly meal voucher
        clt_bonus_annual (float): CLT annual net bonus
        clt_other_benefits (float): CLT other monthly benefits
        pj_invoices (int): Number of annual PJ invoices (12 or 13)
        pj_accounting (float): Monthly accounting costs
        pj_other_costs (float): Other monthly PJ costs
        include_fgts (bool): Include FGTS in equivalence calculation

    Returns:
        dict: Complete calculation breakdown
    """
    # Calculate CLT annual components
    clt_components = get_clt_annual_components(
        clt_salary,
        clt_vavr * 12,
        clt_bonus_annual,
        clt_other_benefits * 12
    )

    # Determine target value (with or without FGTS)
    if include_fgts:
        clt_target_value = clt_components["total_net_income"] + clt_components["annual_fgts"]
    else:
        clt_target_value = clt_components["total_net_income"]

    clt_target_value = round(clt_target_value, 2)

    # Calculate required PJ billing
    pj_aliquota_decimal = pj_aliquota / 100
    total_annual_pj_costs = (pj_accounting + pj_other_costs) * 12

    required_pj_annual_gross = (clt_target_value + total_annual_pj_costs) / (1 - pj_aliquota_decimal)
    required_pj_annual_gross = round(required_pj_annual_gross, 2)
    required_pj_monthly_gross = round(required_pj_annual_gross / pj_invoices, 2)

    # Calculate PJ equivalence
    pj_annual_tax = round(required_pj_annual_gross * pj_aliquota_decimal, 2)
    pj_equivalent_annual_value = round(
        required_pj_annual_gross * (1 - pj_aliquota_decimal) - total_annual_pj_costs,
        2
    )

    equivalence_diff = round(abs(pj_equivalent_annual_value - clt_target_value), 2)

    return {
        "clt_gross_monthly": clt_salary,
        "clt_components": clt_components,
        "clt_target_value": clt_target_value,
        "include_fgts": include_fgts,
        "pj_invoices": pj_invoices,
        "pj_aliquota": pj_aliquota,
        "required_pj_monthly_gross": required_pj_monthly_gross,
        "required_pj_annual_gross": required_pj_annual_gross,
        "pj_annual_tax": pj_annual_tax,
        "pj_annual_costs": total_annual_pj_costs,
        "pj_equivalent_annual_value": pj_equivalent_annual_value,
        "equivalence_diff": equivalence_diff
    }


def calculate_pj_to_clt(pj_billing, pj_aliquota, pj_invoices=12, pj_accounting=0,
                       pj_other_costs=0, clt_vavr_desired=0, clt_bonus_desired=0,
                       clt_other_benefits_desired=0, include_fgts=True):
    """
    Calculate CLT salary equivalent to PJ billing using binary search.
    No closed-form solution exists due to progressive INSS/IRPF.

    Args:
        pj_billing (float): PJ gross monthly billing
        pj_aliquota (float): PJ tax rate (percentage)
        pj_invoices (int): Number of annual invoices (12 or 13)
        pj_accounting (float): Monthly accounting costs
        pj_other_costs (float): Other monthly PJ costs
        clt_vavr_desired (float): Desired CLT monthly meal voucher
        clt_bonus_desired (float): Desired CLT annual bonus
        clt_other_benefits_desired (float): Desired CLT other monthly benefits
        include_fgts (bool): Include FGTS in equivalence

    Returns:
        dict: Complete calculation breakdown including iteration count
    """
    # Calculate PJ net annual value
    pj_annual_gross = pj_billing * pj_invoices
    pj_annual_tax = round(pj_annual_gross * (pj_aliquota / 100), 2)
    pj_annual_costs = (pj_accounting + pj_other_costs) * 12
    pj_net_annual_target = round(pj_annual_gross - pj_annual_tax - pj_annual_costs, 2)

    # Binary search for CLT salary
    low_gross = 1000.0  # Reasonable minimum salary
    high_gross = pj_billing * 1.5  # Upper bound estimate
    max_iterations = 100
    tolerance = 1.00  # R$ 1 acceptable difference
    iteration_count = 0

    annual_vavr = clt_vavr_desired * 12
    annual_bonus = clt_bonus_desired
    annual_other_benefits = clt_other_benefits_desired * 12

    suggested_clt_gross_monthly = 0
    final_clt_components = {}
    clt_equivalent_value = 0

    for i in range(max_iterations):
        iteration_count += 1
        suggested_clt_gross_monthly = (low_gross + high_gross) / 2

        final_clt_components = get_clt_annual_components(
            suggested_clt_gross_monthly,
            annual_vavr,
            annual_bonus,
            annual_other_benefits
        )

        if include_fgts:
            clt_equivalent_value = final_clt_components["total_net_income"] + final_clt_components["annual_fgts"]
        else:
            clt_equivalent_value = final_clt_components["total_net_income"]

        clt_equivalent_value = round(clt_equivalent_value, 2)
        diff = clt_equivalent_value - pj_net_annual_target

        # Check convergence
        if abs(diff) <= tolerance or (high_gross - low_gross) < 0.01:
            break

        # Adjust bounds
        if diff < 0:
            low_gross = suggested_clt_gross_monthly
        else:
            high_gross = suggested_clt_gross_monthly

    suggested_clt_gross_monthly = round(suggested_clt_gross_monthly, 2)
    equivalence_diff = round(abs(clt_equivalent_value - pj_net_annual_target), 2)

    return {
        "pj_monthly_billing": pj_billing,
        "pj_annual_gross": pj_annual_gross,
        "pj_annual_tax": pj_annual_tax,
        "pj_annual_costs": pj_annual_costs,
        "pj_net_annual_target": pj_net_annual_target,
        "pj_aliquota": pj_aliquota,
        "pj_invoices": pj_invoices,
        "suggested_clt_gross_monthly": suggested_clt_gross_monthly,
        "clt_components": final_clt_components,
        "clt_equivalent_value": clt_equivalent_value,
        "include_fgts": include_fgts,
        "equivalence_diff": equivalence_diff,
        "iteration_count": iteration_count
    }


# ========== OUTPUT FORMATTING ==========

def format_currency(value):
    """Format value as Brazilian currency (R$ 1.234,56)"""
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def format_percentage(value):
    """Format value as percentage"""
    return f"{value:.2f}%"


def print_separator(char="=", length=60):
    """Print a separator line"""
    print(char * length)


def print_clt_to_pj_result(result):
    """Print formatted CLT to PJ calculation result"""
    print_separator()
    print("PJ vs CLT Calculator - CLT to PJ")
    print_separator()
    print()

    print("CLT Starting Value:")
    print(f"  Gross Monthly Salary: {format_currency(result['clt_gross_monthly'])}")
    print(f"  Net Monthly Salary: {format_currency(result['clt_components']['net_monthly'])}")
    print(f"  Net Annualized (x13.33): {format_currency(result['clt_components']['net_annualized_salary'])}")
    print(f"  Annual Benefits: {format_currency(result['clt_components']['annual_benefits'])}")
    print(f"  Annual FGTS (8%): {format_currency(result['clt_components']['annual_fgts'])}")
    fgts_status = "included" if result['include_fgts'] else "excluded"
    print(f"  Total Annual Target (FGTS {fgts_status}): {format_currency(result['clt_target_value'])}")
    print()

    print("Required PJ Billing:")
    print(f"  Monthly Gross ({result['pj_invoices']} invoices): {format_currency(result['required_pj_monthly_gross'])}")
    print(f"  Annual Gross: {format_currency(result['required_pj_annual_gross'])}")
    print(f"  Annual Tax ({format_percentage(result['pj_aliquota'])}): {format_currency(result['pj_annual_tax'])}")
    print(f"  Annual Costs: {format_currency(result['pj_annual_costs'])}")
    print(f"  Net Annual: {format_currency(result['pj_equivalent_annual_value'])}")
    print()

    print_separator()
    print("Equivalence Analysis")
    print_separator()
    print(f"Target Value: {format_currency(result['clt_target_value'])}")
    print(f"Actual Value: {format_currency(result['pj_equivalent_annual_value'])}")
    print(f"Difference: {format_currency(result['equivalence_diff'])}", end="")

    if result['clt_target_value'] > 0:
        diff_pct = (result['equivalence_diff'] / result['clt_target_value']) * 100
        print(f" ({diff_pct:.2f}%)")
    else:
        print()

    if result['equivalence_diff'] < 1.00:
        print("\n[OK] Excellent equivalence achieved (difference < R$ 1.00)")
    elif result['equivalence_diff'] < 100.00:
        print("\n[OK] Good equivalence (difference < R$ 100.00)")
    else:
        print("\n[WARNING] Large difference - review parameters")
    print_separator()


def print_pj_to_clt_result(result):
    """Print formatted PJ to CLT calculation result"""
    print_separator()
    print("PJ vs CLT Calculator - PJ to CLT")
    print_separator()
    print()

    print("PJ Starting Value:")
    print(f"  Monthly Billing: {format_currency(result['pj_monthly_billing'])}")
    print(f"  Annual Gross ({result['pj_invoices']} invoices): {format_currency(result['pj_annual_gross'])}")
    print(f"  Annual Tax ({format_percentage(result['pj_aliquota'])}): {format_currency(result['pj_annual_tax'])}")
    print(f"  Annual Costs: {format_currency(result['pj_annual_costs'])}")
    print(f"  Net Annual Target: {format_currency(result['pj_net_annual_target'])}")
    print()

    print("Suggested CLT Salary:")
    print(f"  Gross Monthly: {format_currency(result['suggested_clt_gross_monthly'])}")
    print(f"  Net Monthly: {format_currency(result['clt_components']['net_monthly'])}")
    print(f"  Net Annualized (x13.33): {format_currency(result['clt_components']['net_annualized_salary'])}")
    print(f"  Annual Benefits: {format_currency(result['clt_components']['annual_benefits'])}")
    print(f"  Annual FGTS (8%): {format_currency(result['clt_components']['annual_fgts'])}")
    fgts_status = "included" if result['include_fgts'] else "excluded"
    print(f"  Total Annual (FGTS {fgts_status}): {format_currency(result['clt_equivalent_value'])}")
    print()

    print(f"Binary Search: Converged in {result['iteration_count']} iterations")
    print()

    print_separator()
    print("Equivalence Analysis")
    print_separator()
    print(f"Target Value: {format_currency(result['pj_net_annual_target'])}")
    print(f"Actual Value: {format_currency(result['clt_equivalent_value'])}")
    print(f"Difference: {format_currency(result['equivalence_diff'])}", end="")

    if result['pj_net_annual_target'] > 0:
        diff_pct = (result['equivalence_diff'] / result['pj_net_annual_target']) * 100
        print(f" ({diff_pct:.2f}%)")
    else:
        print()

    if result['equivalence_diff'] < 1.00:
        print("\n[OK] Excellent equivalence achieved (difference < R$ 1.00)")
    elif result['equivalence_diff'] < 100.00:
        print("\n[OK] Good equivalence (difference < R$ 100.00)")
    else:
        print("\n[WARNING] Large difference - review parameters")
    print_separator()


# ========== CLI ==========

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="PJ vs CLT Calculator - Calculate salary equivalence between Brazilian CLT and PJ contracts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # CLT to PJ (basic)
  python3 pj_clt_calculator.py --direction clt-to-pj --clt-salary 10000 --pj-aliquota 6

  # CLT to PJ (with benefits)
  python3 pj_clt_calculator.py --direction clt-to-pj --clt-salary 10000 --pj-aliquota 6 --clt-vavr 600 --clt-bonus-annual 12000

  # PJ to CLT (basic)
  python3 pj_clt_calculator.py --direction pj-to-clt --pj-billing 15000 --pj-aliquota 6

  # PJ to CLT (with desired benefits)
  python3 pj_clt_calculator.py --direction pj-to-clt --pj-billing 15000 --pj-aliquota 6 --clt-vavr-desired 600 --clt-bonus-desired 5000
        """
    )

    parser.add_argument("--direction", choices=["clt-to-pj", "pj-to-clt"], required=True,
                       help="Conversion direction")

    # CLT parameters
    parser.add_argument("--clt-salary", type=float,
                       help="CLT gross monthly salary")
    parser.add_argument("--clt-vavr", type=float, default=0,
                       help="CLT meal voucher/food allowance (monthly)")
    parser.add_argument("--clt-bonus-annual", type=float, default=0,
                       help="CLT annual net bonus")
    parser.add_argument("--clt-other-benefits", type=float, default=0,
                       help="CLT other monthly benefits")

    # PJ parameters
    parser.add_argument("--pj-billing", type=float,
                       help="PJ gross monthly billing")
    parser.add_argument("--pj-aliquota", type=float,
                       help="PJ tax rate (percentage, e.g., 6 for 6%%)")
    parser.add_argument("--pj-invoices", type=int, choices=[12, 13], default=12,
                       help="Number of annual invoices (default: 12)")
    parser.add_argument("--pj-accounting", type=float, default=0,
                       help="Monthly accounting costs")
    parser.add_argument("--pj-other-costs", type=float, default=0,
                       help="Other monthly PJ costs")

    # CLT desired benefits (for PJ to CLT)
    parser.add_argument("--clt-vavr-desired", type=float, default=0,
                       help="Desired CLT meal voucher (monthly) for PJ→CLT")
    parser.add_argument("--clt-bonus-desired", type=float, default=0,
                       help="Desired CLT annual bonus for PJ→CLT")
    parser.add_argument("--clt-other-benefits-desired", type=float, default=0,
                       help="Desired CLT other monthly benefits for PJ→CLT")

    # Options
    parser.add_argument("--include-fgts", action="store_true", default=True,
                       help="Include FGTS in equivalence (default: True)")
    parser.add_argument("--no-include-fgts", action="store_false", dest="include_fgts",
                       help="Exclude FGTS from equivalence")

    return parser.parse_args()


def main():
    """Main execution function"""
    args = parse_arguments()

    if eam_client is not None:
        try:
            eam_client.on_first_run(
                skill_name=SKILL_NAME,
                skill_version=SKILL_VERSION,
                source="github",
            )
        except Exception:
            pass

    # Validate requirements
    if not args.pj_aliquota:
        print("❌ Error: --pj-aliquota is required", file=sys.stderr)
        sys.exit(1)

    if args.direction == "clt-to-pj":
        if not args.clt_salary:
            print("❌ Error: --clt-salary is required for clt-to-pj", file=sys.stderr)
            sys.exit(1)

        result = calculate_clt_to_pj(
            clt_salary=args.clt_salary,
            pj_aliquota=args.pj_aliquota,
            clt_vavr=args.clt_vavr,
            clt_bonus_annual=args.clt_bonus_annual,
            clt_other_benefits=args.clt_other_benefits,
            pj_invoices=args.pj_invoices,
            pj_accounting=args.pj_accounting,
            pj_other_costs=args.pj_other_costs,
            include_fgts=args.include_fgts
        )
        print_clt_to_pj_result(result)

    elif args.direction == "pj-to-clt":
        if not args.pj_billing:
            print("❌ Error: --pj-billing is required for pj-to-clt", file=sys.stderr)
            sys.exit(1)

        result = calculate_pj_to_clt(
            pj_billing=args.pj_billing,
            pj_aliquota=args.pj_aliquota,
            pj_invoices=args.pj_invoices,
            pj_accounting=args.pj_accounting,
            pj_other_costs=args.pj_other_costs,
            clt_vavr_desired=args.clt_vavr_desired,
            clt_bonus_desired=args.clt_bonus_desired,
            clt_other_benefits_desired=args.clt_other_benefits_desired,
            include_fgts=args.include_fgts
        )
        print_pj_to_clt_result(result)

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=pj-vs-clt-calculator")


if __name__ == "__main__":
    main()
