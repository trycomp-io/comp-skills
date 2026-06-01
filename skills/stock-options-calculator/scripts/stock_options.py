#!/usr/bin/env python3
"""
stock_options.py — Calculadora de valor de Stock Options em empresas de
capital fechado. Modela vesting, diluição, cenários de exit e dá talking
points alinhados ao framework do artigo Cajuína "Stock Options em empresas
de capital fechado" (Filipe Ducas).

A tese do artigo: equity privado não compete em liquidez — compete em
multiplicação. Por isso o output é estruturado em CENÁRIOS (3x / 5x / 10x /
50x) e não num valor único.

Uso:
    python3 stock_options.py \\
        --grant 10000 --strike 5 --fmv 5 \\
        --vesting-years 4 --cliff-months 12 \\
        --current-valuation 50000000 \\
        --shares-outstanding 10000000 \\
        --rounds-until-exit 2 --dilution-per-round 20
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "stock-options-calculator"
SKILL_VERSION = "1.0.0"

DEFAULT_SCENARIOS = [3, 5, 10, 50]


def fmt_money(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"R$ {v/1_000_000:,.2f}M".replace(",", "X").replace(".", ",").replace("X", ".")
    if abs(v) >= 1_000:
        return f"R$ {v/1_000:,.1f}k".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def vesting_timeline(grant: int, vesting_years: float, cliff_months: int) -> list[tuple[str, int, float]]:
    """Retorna [(label, options_vested_acumulado, pct_vested), ...] anual."""
    total_months = int(vesting_years * 12)
    timeline = []
    for month in range(0, total_months + 1, 12):
        if month < cliff_months:
            vested = 0
        else:
            vested = int(round(grant * (month / total_months)))
        pct = vested / grant * 100 if grant else 0
        year = month // 12
        timeline.append((f"Ano {year}", vested, pct))
    return timeline


def calculate_scenarios(
    grant: int,
    strike: float,
    fmv: float,
    current_valuation: float,
    shares_outstanding: float,
    multipliers: list[float],
    rounds_until_exit: int,
    dilution_per_round: float,
) -> list[dict]:
    """Pra cada multiplier, calcula valor de exit por opção e total."""
    pct_of_company = (grant / shares_outstanding) if shares_outstanding > 0 else 0
    dilution_factor = (1 - dilution_per_round / 100) ** rounds_until_exit  # ex: 0.8^2 = 0.64
    pct_after_dilution = pct_of_company * dilution_factor

    results = []
    for mult in multipliers:
        exit_val = current_valuation * mult
        proceeds_pre_strike = exit_val * pct_after_dilution
        strike_cost = grant * strike
        net_proceeds = proceeds_pre_strike - strike_cost
        per_option = net_proceeds / grant if grant else 0
        results.append({
            "multiplier": mult,
            "exit_valuation": exit_val,
            "pct_after_dilution": pct_after_dilution,
            "proceeds_gross": proceeds_pre_strike,
            "strike_cost": strike_cost,
            "net_proceeds": net_proceeds,
            "per_option": per_option,
            "vs_strike_multiple": (per_option + strike) / strike if strike else None,
        })
    return results


TALKING_POINTS = """
1. EQUITY ≠ DINHEIRO LÍQUIDO. Options não competem em cash; competem em multiplicação.
   Em 5 anos, a tese é a empresa valer 5-10x o que vale hoje. Você ganha proporcionalmente.

2. SEM CASH SAINDO HOJE. Strike só é exercido em exit (ou cliff trigger). Você não
   gasta um centavo enquanto trabalha aqui.

3. BINÁRIO: ESCALA OU ZERO. Honesto: ou a empresa cresce e isso vira dinheiro real
   (cenários 5x+), ou vira zero. Não tem meio termo confortável.

4. VESTING ALINHA DECISÃO. 4 anos com cliff de 1 ano significa que decisão de ficar
   é renovada a cada ano. É um contrato de parceria, não golden handcuff.

5. PARCERIA, NÃO COMPENSAÇÃO. A pergunta certa é "que tipo de parceiro eu quero ser?"
   — não "quanto isso me paga". Quem influencia o valor de longo prazo do negócio
   compartilha o valor que ajuda a criar.
"""


def main() -> int:
    p = argparse.ArgumentParser(
        description="Calculadora de Stock Options em empresas de capital fechado (BR).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--grant", type=int, required=True, help="Quantidade de opções concedidas")
    p.add_argument("--strike", type=float, required=True, help="Strike price por opção (R$)")
    p.add_argument("--fmv", type=float, required=True, help="Fair Market Value atual por opção (R$, do último 409A/valuation)")
    p.add_argument("--vesting-years", type=float, default=4, help="Período de vesting (default 4 anos)")
    p.add_argument("--cliff-months", type=int, default=12, help="Cliff em meses (default 12)")
    p.add_argument("--current-valuation", type=float, required=True, help="Valuation atual da empresa (R$)")
    p.add_argument("--shares-outstanding", type=float, required=True, help="Total de shares (fully diluted)")
    p.add_argument("--rounds-until-exit", type=int, default=2, help="Rounds esperados até exit (default 2)")
    p.add_argument("--dilution-per-round", type=float, default=20, help="Diluição esperada por round em %% (default 20)")
    p.add_argument("--multipliers", nargs="+", type=float, default=DEFAULT_SCENARIOS,
                   help="Multiplicadores de exit a simular (default 3 5 10 50)")
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    print()
    print("=" * 64)
    print("  STOCK OPTIONS — Empresa de capital fechado")
    print("=" * 64)
    print(f"  Grant:                  {args.grant:,} opções".replace(",", "."))
    print(f"  Strike:                 {fmt_money(args.strike)} / opção")
    print(f"  FMV atual:              {fmt_money(args.fmv)} / opção")
    print(f"  Vesting:                {args.vesting_years:g} anos, cliff {args.cliff_months}m")
    print(f"  Valuation atual:        {fmt_money(args.current_valuation)}")
    print(f"  Total shares (FD):      {args.shares_outstanding:,.0f}".replace(",", "."))
    pct_now = args.grant / args.shares_outstanding * 100 if args.shares_outstanding else 0
    print(f"  % da empresa hoje:      {pct_now:.3f}%")
    print(f"  Rounds até exit:        {args.rounds_until_exit} × {args.dilution_per_round:.0f}% diluição")
    pct_diluted = pct_now * ((1 - args.dilution_per_round / 100) ** args.rounds_until_exit)
    print(f"  % no exit (diluído):    {pct_diluted:.3f}%")
    print()

    # Valor intrínseco hoje
    intrinsic_today = (args.fmv - args.strike) * args.grant
    print(f"  VALOR INTRÍNSECO HOJE:  {fmt_money(intrinsic_today)} (FMV - strike, antes de IR)")
    print("  (esse número é hipotético — você não pode vender em empresa fechada)")
    print()

    # Vesting timeline
    print("  VESTING TIMELINE")
    print("  " + "-" * 56)
    for label, vested, pct in vesting_timeline(args.grant, args.vesting_years, args.cliff_months):
        bar = "█" * int(pct / 5)
        print(f"  {label}: {vested:>8,} opções ({pct:>5.1f}%)  {bar}".replace(",", "."))
    print()

    # Cenários de exit
    scenarios = calculate_scenarios(
        args.grant, args.strike, args.fmv,
        args.current_valuation, args.shares_outstanding,
        args.multipliers, args.rounds_until_exit, args.dilution_per_round,
    )
    print("  CENÁRIOS DE EXIT (após diluição, antes de impostos)")
    print("  " + "-" * 64)
    print(f"  {'Multiplier':<12} {'Exit Valuation':>18} {'Net pro você':>16} {'×Strike':>10}")
    for s in scenarios:
        mult_label = f"{s['multiplier']:g}x"
        net = fmt_money(s["net_proceeds"])
        vs_strike = f"{s['vs_strike_multiple']:.1f}x" if s["vs_strike_multiple"] is not None else "—"
        print(f"  {mult_label:<12} {fmt_money(s['exit_valuation']):>18} {net:>16} {vs_strike:>10}")
    print()
    print(f"  Nota: impostos sobre ganho de capital (15% até R$5M, escalonado) descontam")
    print(f"        do 'Net pro você'. Use o número líquido como teto otimista.")
    print()

    print("=" * 64)
    print("  TALKING POINTS — pra conversa com candidato/colaborador")
    print("=" * 64)
    print(TALKING_POINTS)
    print()
    print("  Framework: artigo 'Stock Options em empresas de capital fechado'")
    print("  da coluna Comp na Cajuína:")
    print("  https://cajuina.org/principais/coluna-comp/stock-options/")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=stock-options-calculator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
