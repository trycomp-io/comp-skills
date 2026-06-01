#!/usr/bin/env python3
"""
Custo de Demissão CLT — calcula o custo total de uma rescisão trabalhista
no Brasil para os 4 tipos mais comuns:

  - sem_justa_causa   (empregador demite sem motivo)
  - com_justa_causa   (empregador demite por falta grave)
  - pedido_demissao   (colaborador pede para sair)
  - acordo            (rescisão por mútuo acordo, Lei 13.467/2017)

Decompõe em todas as verbas (saldo, aviso, 13º, férias, FGTS, INSS, IRPF)
e mostra o custo total para o empregador.

Uso:
    python3 custo_demissao.py \\
        --tipo sem_justa_causa \\
        --salario 10000 \\
        --data-admissao 2022-01-15 \\
        --data-demissao 2026-05-30

Veja --help para todas as flags.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# Lead capture / telemetry — best-effort, never blocks the calc.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "custo-demissao-calculator"
SKILL_VERSION = "1.0.0"


# ========== Tax tables 2024/2025 ==========

INSS_TABLE = [
    {"limit": 1412.00, "rate": 0.075, "deduction": 0.00},
    {"limit": 2666.68, "rate": 0.09,  "deduction": 21.18},
    {"limit": 4000.03, "rate": 0.12,  "deduction": 101.18},
    {"limit": 7786.02, "rate": 0.14,  "deduction": 181.18},
]
INSS_CEILING = 7786.02
INSS_MAX = 908.85

IRPF_TABLE = [
    {"limit": 2259.20, "rate": 0.0,   "deduction": 0.00},
    {"limit": 2826.65, "rate": 0.075, "deduction": 169.44},
    {"limit": 3751.05, "rate": 0.15,  "deduction": 381.44},
    {"limit": 4664.68, "rate": 0.225, "deduction": 662.77},
    {"limit": float("inf"), "rate": 0.275, "deduction": 896.00},
]

FGTS_RATE = 0.08


# ========== Tax helpers ==========


def inss(gross: float) -> float:
    if gross >= INSS_CEILING:
        return round(INSS_MAX, 2)
    for b in INSS_TABLE:
        if gross <= b["limit"]:
            return round(gross * b["rate"] - b["deduction"], 2)
    return round(INSS_MAX, 2)


def irpf(base: float) -> float:
    for b in IRPF_TABLE:
        if base <= b["limit"]:
            return round(max(0.0, base * b["rate"] - b["deduction"]), 2)
    return 0.0


# ========== Domain ==========


@dataclass
class Inputs:
    tipo: str
    salario: float
    admissao: date
    demissao: date
    aviso: str = "indenizado"  # indenizado | trabalhado | dispensado
    ferias_vencidas: int = 0  # 0 ou 1 período de 30 dias a vencer
    fgts_saldo: float | None = None  # se None, estima 8% × meses × salário
    beneficios_extras_mes: float = 0.0  # outros benefícios proporcionais ao saldo (ex: VR/VA)


@dataclass
class Verba:
    nome: str
    valor: float
    detalhe: str = ""


@dataclass
class Result:
    inputs: Inputs
    verbas_credito: list[Verba] = field(default_factory=list)
    verbas_debito: list[Verba] = field(default_factory=list)
    fgts_saque_disponivel: float = 0.0
    multa_fgts: float = 0.0
    encargos_empregador: list[Verba] = field(default_factory=list)


# ========== Util ==========


def months_between(start: date, end: date) -> int:
    """Months between dates counting whole months. Same day counts."""
    return (end.year - start.year) * 12 + (end.month - start.month) - (1 if end.day < start.day else 0)


def years_complete(start: date, end: date) -> int:
    """Whole years between dates (used for aviso prévio: +3 days per year)."""
    y = end.year - start.year
    if (end.month, end.day) < (start.month, start.day):
        y -= 1
    return max(0, y)


def days_in_month(d: date) -> int:
    if d.month == 12:
        return 31
    from calendar import monthrange
    return monthrange(d.year, d.month)[1]


# ========== Verbas ==========


def saldo_salario(salario: float, demissao: date) -> Verba:
    days = demissao.day
    dim = days_in_month(demissao)
    valor = round(salario * days / dim, 2)
    return Verba("Saldo de salário", valor, f"{days}/{dim} dias do mês")


def aviso_previo_dias(admissao: date, demissao: date) -> int:
    """30 dias base + 3 por ano completo, capado em 90 dias."""
    anos = years_complete(admissao, demissao)
    return min(30 + 3 * anos, 90)


def aviso_previo_indenizado(salario: float, dias: int) -> Verba:
    valor = round(salario * dias / 30, 2)
    return Verba("Aviso prévio indenizado", valor, f"{dias} dias")


def decimo_terceiro_proporcional(salario: float, demissao: date) -> Verba:
    """Avos do 13º contam meses com 15+ dias trabalhados no ano corrente."""
    meses = demissao.month
    # mês de demissão conta se >= 15 dias
    if demissao.day < 15:
        meses -= 1
    meses = max(0, meses)
    valor = round(salario * meses / 12, 2)
    return Verba("13º proporcional", valor, f"{meses}/12 avos")


def ferias_vencidas_v(salario: float) -> Verba:
    base = salario
    terco = base / 3
    valor = round(base + terco, 2)
    return Verba("Férias vencidas + 1/3", valor, "1 período integral")


def ferias_proporcionais(salario: float, admissao: date, demissao: date) -> Verba:
    """
    Avos de férias proporcionais no período aquisitivo corrente.
    Período aquisitivo = ano contado a partir do último aniversário de admissão.
    """
    # ultima data de início de período aquisitivo
    inicio_aquisitivo = date(demissao.year, admissao.month, admissao.day)
    if inicio_aquisitivo > demissao:
        inicio_aquisitivo = date(demissao.year - 1, admissao.month, admissao.day)
    meses = (demissao.year - inicio_aquisitivo.year) * 12 + (demissao.month - inicio_aquisitivo.month)
    if demissao.day < inicio_aquisitivo.day:
        meses -= 1
    meses = max(0, meses)
    base = salario * meses / 12
    terco = base / 3
    valor = round(base + terco, 2)
    return Verba("Férias proporcionais + 1/3", valor, f"{meses}/12 avos")


def estimar_fgts_saldo(salario: float, admissao: date, demissao: date) -> float:
    meses = months_between(admissao, demissao)
    return round(salario * FGTS_RATE * meses, 2)


# ========== Cálculo por tipo ==========


def calcular(inputs: Inputs) -> Result:
    r = Result(inputs=inputs)
    s = inputs.salario

    # Saldo de salário — todos os tipos
    saldo = saldo_salario(s, inputs.demissao)
    r.verbas_credito.append(saldo)

    # Benefícios extras proporcionais (VR/VA, etc.)
    if inputs.beneficios_extras_mes > 0:
        days = inputs.demissao.day
        dim = days_in_month(inputs.demissao)
        b = round(inputs.beneficios_extras_mes * days / dim, 2)
        r.verbas_credito.append(Verba("Benefícios extras (proporcional)", b, f"{days}/{dim} dias"))

    # Férias vencidas — devidas em todos os tipos, se houver
    if inputs.ferias_vencidas:
        r.verbas_credito.append(ferias_vencidas_v(s))

    # FGTS saldo
    fgts = inputs.fgts_saldo if inputs.fgts_saldo is not None else estimar_fgts_saldo(s, inputs.admissao, inputs.demissao)

    tipo = inputs.tipo

    if tipo == "sem_justa_causa":
        dias_aviso = aviso_previo_dias(inputs.admissao, inputs.demissao)
        if inputs.aviso == "indenizado":
            r.verbas_credito.append(aviso_previo_indenizado(s, dias_aviso))
        elif inputs.aviso == "trabalhado":
            r.verbas_credito.append(Verba("Aviso prévio trabalhado", 0.0, f"{dias_aviso} dias trabalhados (sem custo extra)"))
        # "dispensado" = nem trabalha nem recebe (raro, geralmente acordo informal)

        r.verbas_credito.append(decimo_terceiro_proporcional(s, inputs.demissao))
        r.verbas_credito.append(ferias_proporcionais(s, inputs.admissao, inputs.demissao))
        r.multa_fgts = round(fgts * 0.40, 2)
        r.fgts_saque_disponivel = round(fgts, 2)

    elif tipo == "com_justa_causa":
        # Apenas saldo, férias vencidas (se houver), férias proporcionais NÃO devidas
        # 13º proporcional NÃO devido (entendimento majoritário)
        pass

    elif tipo == "pedido_demissao":
        # Colaborador deve aviso ao empregador (descontado se não trabalhado)
        dias_aviso = aviso_previo_dias(inputs.admissao, inputs.demissao)
        if inputs.aviso == "trabalhado":
            pass  # cumpriu, sem desconto
        else:
            desc = round(s * dias_aviso / 30, 2)
            r.verbas_debito.append(Verba("Desconto aviso prévio (não cumprido)", desc, f"{dias_aviso} dias"))
        r.verbas_credito.append(decimo_terceiro_proporcional(s, inputs.demissao))
        r.verbas_credito.append(ferias_proporcionais(s, inputs.admissao, inputs.demissao))
        # Sem multa FGTS, sem saque, sem seguro desemprego

    elif tipo == "acordo":
        dias_aviso = aviso_previo_dias(inputs.admissao, inputs.demissao)
        # Aviso indenizado pago pela metade
        valor_aviso = round(s * dias_aviso / 30 * 0.5, 2)
        r.verbas_credito.append(Verba("Aviso prévio indenizado (50% — acordo)", valor_aviso, f"{dias_aviso} dias × 50%"))
        r.verbas_credito.append(decimo_terceiro_proporcional(s, inputs.demissao))
        r.verbas_credito.append(ferias_proporcionais(s, inputs.admissao, inputs.demissao))
        r.multa_fgts = round(fgts * 0.20, 2)  # 50% da multa de 40%
        r.fgts_saque_disponivel = round(fgts * 0.80, 2)  # 80% do FGTS

    else:
        raise ValueError(f"Tipo de demissão desconhecido: {tipo}")

    # Encargos descontados
    saldo_v = next((v.valor for v in r.verbas_credito if v.nome == "Saldo de salário"), 0.0)
    decimo_v = next((v.valor for v in r.verbas_credito if v.nome == "13º proporcional"), 0.0)

    # INSS sobre saldo e sobre 13º (cálculo separado)
    if saldo_v > 0:
        inss_saldo = inss(saldo_v)
        r.verbas_debito.append(Verba("INSS sobre saldo", inss_saldo))
        base_irpf_saldo = saldo_v - inss_saldo
        irpf_saldo = irpf(base_irpf_saldo)
        if irpf_saldo > 0:
            r.verbas_debito.append(Verba("IRPF sobre saldo", irpf_saldo))

    if decimo_v > 0:
        inss_13 = inss(decimo_v)
        r.verbas_debito.append(Verba("INSS sobre 13º", inss_13))
        base_irpf_13 = decimo_v - inss_13
        irpf_13 = irpf(base_irpf_13)
        if irpf_13 > 0:
            r.verbas_debito.append(Verba("IRPF sobre 13º", irpf_13))

    # Encargos do empregador (custos invisíveis na rescisão)
    if tipo in ("sem_justa_causa", "acordo"):
        # FGTS sobre saldo + 13º + aviso indenizado + férias indenizadas
        bases_fgts = sum(v.valor for v in r.verbas_credito if v.nome in (
            "Saldo de salário", "13º proporcional",
            "Aviso prévio indenizado", "Aviso prévio indenizado (50% — acordo)",
            "Férias proporcionais + 1/3", "Férias vencidas + 1/3",
        ))
        fgts_mes_rescisao = round(bases_fgts * FGTS_RATE, 2)
        r.encargos_empregador.append(Verba("FGTS sobre verbas rescisórias", fgts_mes_rescisao))

    return r


# ========== Output ==========


def fmt(v: float) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def print_result(r: Result) -> None:
    tipo_label = {
        "sem_justa_causa": "Sem justa causa (empregador)",
        "com_justa_causa": "Com justa causa (empregador)",
        "pedido_demissao": "Pedido de demissão (colaborador)",
        "acordo":          "Acordo mútuo (art. 484-A)",
    }[r.inputs.tipo]

    print()
    print("=" * 64)
    print(f"  RESCISÃO CLT — {tipo_label}")
    print("=" * 64)
    meses = months_between(r.inputs.admissao, r.inputs.demissao)
    anos = years_complete(r.inputs.admissao, r.inputs.demissao)
    print(f"  Salário base:     {fmt(r.inputs.salario)}")
    print(f"  Admissão:         {r.inputs.admissao.isoformat()}")
    print(f"  Demissão:         {r.inputs.demissao.isoformat()}")
    print(f"  Tempo de empresa: {anos} ano(s) ({meses} meses)")
    if r.inputs.aviso and r.inputs.tipo in ("sem_justa_causa", "pedido_demissao"):
        print(f"  Aviso prévio:     {r.inputs.aviso}")
    print()

    print("  VERBAS DEVIDAS AO COLABORADOR")
    print("  " + "-" * 60)
    total_credito = 0.0
    for v in r.verbas_credito:
        line = f"    {v.nome:<42}  {fmt(v.valor):>14}"
        print(line + (f"  ({v.detalhe})" if v.detalhe else ""))
        total_credito += v.valor
    print(f"    {'Subtotal bruto':<42}  {fmt(round(total_credito, 2)):>14}")
    print()

    if r.verbas_debito:
        print("  DESCONTOS")
        print("  " + "-" * 60)
        total_debito = 0.0
        for v in r.verbas_debito:
            line = f"    {v.nome:<42}  {fmt(v.valor):>14}"
            print(line + (f"  ({v.detalhe})" if v.detalhe else ""))
            total_debito += v.valor
        print(f"    {'Total descontos':<42}  {fmt(round(total_debito, 2)):>14}")
        print()

        liquido = round(total_credito - total_debito, 2)
    else:
        liquido = round(total_credito, 2)

    print("  RESUMO PARA O COLABORADOR")
    print("  " + "-" * 60)
    print(f"    {'Total LÍQUIDO a receber':<42}  {fmt(liquido):>14}")
    if r.multa_fgts > 0:
        print(f"    {'Multa FGTS (paga via guia GRRF)':<42}  {fmt(r.multa_fgts):>14}")
    if r.fgts_saque_disponivel > 0:
        print(f"    {'Saque FGTS disponível':<42}  {fmt(r.fgts_saque_disponivel):>14}")
    print()

    if r.encargos_empregador:
        print("  CUSTO ADICIONAL PARA O EMPREGADOR")
        print("  " + "-" * 60)
        for v in r.encargos_empregador:
            print(f"    {v.nome:<42}  {fmt(v.valor):>14}")
        print()

    custo_empregador = round(
        total_credito + r.multa_fgts + sum(v.valor for v in r.encargos_empregador),
        2,
    )
    print("=" * 64)
    print(f"  CUSTO TOTAL PARA O EMPREGADOR:  {fmt(custo_empregador)}")
    print("=" * 64)


# ========== CLI ==========


def parse_date(s: str) -> date:
    return date.fromisoformat(s)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Calculadora de custo de rescisão CLT (Brasil).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Demissão sem justa causa, R$ 10k, 4 anos de casa, aviso indenizado
  python3 custo_demissao.py --tipo sem_justa_causa \\
      --salario 10000 --data-admissao 2022-01-15 --data-demissao 2026-05-30

  # Acordo mútuo, R$ 8k, 2 anos
  python3 custo_demissao.py --tipo acordo \\
      --salario 8000 --data-admissao 2024-03-01 --data-demissao 2026-05-30

  # Pedido de demissão, sem cumprimento de aviso
  python3 custo_demissao.py --tipo pedido_demissao \\
      --salario 6000 --data-admissao 2023-06-01 --data-demissao 2026-05-30 \\
      --aviso indenizado
""",
    )
    p.add_argument("--tipo", required=True,
                   choices=["sem_justa_causa", "com_justa_causa", "pedido_demissao", "acordo"])
    p.add_argument("--salario", type=float, required=True, help="Salário bruto mensal")
    p.add_argument("--data-admissao", required=True, type=parse_date, help="YYYY-MM-DD")
    p.add_argument("--data-demissao", required=True, type=parse_date, help="YYYY-MM-DD")
    p.add_argument("--aviso", default="indenizado", choices=["indenizado", "trabalhado", "dispensado"])
    p.add_argument("--ferias-vencidas", type=int, default=0, choices=[0, 1],
                   help="Quantidade de períodos vencidos de 30 dias (0 ou 1)")
    p.add_argument("--fgts-saldo", type=float, default=None,
                   help="Saldo FGTS real (R$). Se não passado, estima 8%% × meses × salário")
    p.add_argument("--beneficios-extras", type=float, default=0.0,
                   help="Outros benefícios mensais que entram proporcional ao saldo (ex: VR)")
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    inputs = Inputs(
        tipo=args.tipo,
        salario=args.salario,
        admissao=args.data_admissao,
        demissao=args.data_demissao,
        aviso=args.aviso,
        ferias_vencidas=args.ferias_vencidas,
        fgts_saldo=args.fgts_saldo,
        beneficios_extras_mes=args.beneficios_extras,
    )

    if inputs.demissao < inputs.admissao:
        print("Erro: data de demissão anterior à admissão.", file=sys.stderr)
        return 1

    r = calcular(inputs)
    print_result(r)

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=custo-demissao-calculator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
