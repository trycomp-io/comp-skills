#!/usr/bin/env python3
"""
Custo (oculto) de Turnover — calcula o custo real de perder um colaborador,
decompondo em 8 componentes (separação, recrutamento, onboarding, perda de
produtividade durante o ramp, impacto no time, perda de conhecimento, perda
de satisfação do cliente e erros/retrabalho).

Metodologia baseada no artigo "O custo oculto do turnover" da coluna Comp na
Cajuína (https://cajuina.org/principais/coluna-comp/o-custo-oculto-do-turnover/),
com multiplicadores de referência por nível de cargo:

  - operational:  ~60% do salário anual (range 50-75%)
  - specialist:   ~100%
  - manager:      ~125% (range 100-150%)
  - executive:    ~200%+ (referência: 213% pra cargos altamente qualificados)

Dois modos:
  - quick:    informa só salário anual + nível, usa multiplicador
  - detailed: informa cada componente; faltantes caem na estimativa do modo quick

Modo batch via --input CSV (uma linha por desligamento).

Uso:
    # Quick — manager R$120k
    python3 custo_turnover.py --quick --annual-salary 120000 --level manager

    # Detailed — replica o exemplo do artigo
    python3 custo_turnover.py --annual-salary 120000 --level manager \\
        --separation 20000 --recruitment 21500 --training 10000 \\
        --ramp-months 6 --ramp-productivity-gap 0.5 --team-impact 5000

    # Batch
    python3 custo_turnover.py --input desligamentos.csv --output custos.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# Lead capture / telemetry — best-effort, never blocks the calc.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "custo-turnover-calculator"
SKILL_VERSION = "1.0.0"


# ========== Multiplicadores por nível (% do salário anual) ==========
# Fonte: artigo Cajuína + literatura SHRM/HBR.
LEVEL_MULTIPLIERS = {
    "operational": 0.60,   # entry/operacional (50-75%, mediana ~60%)
    "specialist":  1.00,   # técnico/especialista
    "manager":     1.25,   # gerencial (100-150%, mediana 125%)
    "executive":   2.00,   # executivo/sr leadership (200%+)
}

# Pesos default por componente, quando NÃO informado (fallback do modo quick).
# Soma deve aproximar o multiplicador do nível. Calibrado pra um manager.
DEFAULT_COMPONENT_WEIGHTS = {
    "separation":       0.15,   # rescisão + jurídico
    "recruitment":      0.20,   # divulgação + recruiter + tempo gestor
    "training":         0.10,   # onboarding + material
    "productivity":     0.30,   # 6 meses × 50% gap (estimativa padrão)
    "team_impact":      0.05,   # moral, sobrecarga
    "knowledge_loss":   0.10,   # expertise embutida que sai
    "customer_impact":  0.05,   # apenas pra cargos client-facing
    "rework":           0.05,   # erros de quem está aprendendo
}


@dataclass
class Inputs:
    annual_salary: float
    level: str = "specialist"
    # detailed (None = use estimativa)
    separation: float | None = None
    recruitment: float | None = None
    training: float | None = None
    ramp_months: float = 6.0
    ramp_productivity_gap: float = 0.5
    team_impact: float | None = None
    knowledge_loss: float | None = None
    customer_impact: float | None = None
    rework: float | None = None
    role_label: str = ""  # opcional, só pra label no output (batch)


@dataclass
class Component:
    name: str
    label_pt: str
    value: float
    estimated: bool   # True se a gente estimou em vez do CHRO ter informado
    detail: str = ""


@dataclass
class Result:
    inputs: Inputs
    components: list[Component] = field(default_factory=list)
    multiplier: float = 0.0

    @property
    def total(self) -> float:
        return round(sum(c.value for c in self.components), 2)

    @property
    def pct_of_salary(self) -> float:
        return round((self.total / self.inputs.annual_salary) * 100, 1) if self.inputs.annual_salary > 0 else 0.0


def _estimate(weight: float, annual_salary: float, level_multiplier: float) -> float:
    """Calcula valor estimado de um componente baseado no peso × salário × multiplicador."""
    return round(weight * annual_salary * level_multiplier, 2)


def _productivity_loss(monthly_salary: float, ramp_months: float, gap: float) -> float:
    """Perda real de produtividade durante o ramp: ramp_months × gap × salário mensal."""
    return round(monthly_salary * ramp_months * gap, 2)


def calcular(inp: Inputs) -> Result:
    r = Result(inputs=inp)
    multiplier = LEVEL_MULTIPLIERS.get(inp.level, LEVEL_MULTIPLIERS["specialist"])
    r.multiplier = multiplier
    monthly = inp.annual_salary / 12

    def add(name: str, label: str, user_value: float | None, weight_key: str, detail: str = ""):
        if user_value is not None and user_value >= 0:
            r.components.append(Component(name, label, round(user_value, 2), False, detail))
        else:
            est = _estimate(DEFAULT_COMPONENT_WEIGHTS[weight_key], inp.annual_salary, multiplier)
            r.components.append(Component(name, label, est, True, f"estimado ({DEFAULT_COMPONENT_WEIGHTS[weight_key]*100:.0f}% × {multiplier*100:.0f}% × salário anual)"))

    add("separation",   "Separação (rescisão + jurídico)", inp.separation,   "separation")
    add("recruitment",  "Recrutamento (divulgação + recruiter + tempo gestor)", inp.recruitment, "recruitment")
    add("training",     "Onboarding e treinamento", inp.training, "training")

    # Productivity loss: especial — sempre calculada com fórmula direta se ramp_months e gap forem fornecidos
    if inp.ramp_months > 0 and inp.ramp_productivity_gap > 0:
        prod_loss = _productivity_loss(monthly, inp.ramp_months, inp.ramp_productivity_gap)
        r.components.append(Component(
            "productivity",
            "Perda de produtividade durante o ramp",
            prod_loss,
            False,
            f"{inp.ramp_months:g} meses × {inp.ramp_productivity_gap*100:.0f}% gap × salário mensal",
        ))
    else:
        add("productivity", "Perda de produtividade durante o ramp", None, "productivity")

    add("team_impact",     "Impacto no time (moral + sobrecarga)", inp.team_impact,     "team_impact")
    add("knowledge_loss",  "Perda de conhecimento e expertise", inp.knowledge_loss,  "knowledge_loss")
    add("customer_impact", "Impacto em cliente / satisfação", inp.customer_impact, "customer_impact")
    add("rework",          "Erros e retrabalho durante o aprendizado", inp.rework, "rework")

    return r


# ========== Output ==========


def fmt_money(v: float) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def print_result(r: Result) -> None:
    inp = r.inputs
    level_label = {
        "operational": "Operacional / Entry",
        "specialist":  "Técnico / Especialista",
        "manager":     "Gerencial",
        "executive":   "Executivo / Senior Leadership",
    }.get(inp.level, inp.level)

    print()
    print("=" * 68)
    print("  CUSTO REAL DE TURNOVER" + (f" — {inp.role_label}" if inp.role_label else ""))
    print("=" * 68)
    print(f"  Salário anual:         {fmt_money(inp.annual_salary)}")
    print(f"  Nível:                 {level_label} (multiplicador referência: {r.multiplier*100:.0f}%)")
    print(f"  Janela de ramp:        {inp.ramp_months:g} meses × {inp.ramp_productivity_gap*100:.0f}% gap")
    print()

    print("  COMPONENTES DE CUSTO")
    print("  " + "-" * 64)
    for c in r.components:
        flag = " (est.)" if c.estimated else ""
        line = f"    {c.label_pt + flag:<46}  {fmt_money(c.value):>14}"
        print(line)
        if c.detail:
            print(f"      {c.detail}")
    print()

    print("=" * 68)
    print(f"  CUSTO TOTAL DE TURNOVER:  {fmt_money(r.total)}")
    print(f"  Equivalente a {r.pct_of_salary:.1f}% do salário anual (referência nível: {r.multiplier*100:.0f}%)")
    print("=" * 68)

    estimados = sum(1 for c in r.components if c.estimated)
    if estimados > 0:
        print(f"\n  Nota: {estimados} de {len(r.components)} componentes foram estimados. Para mais precisão,")
        print(f"        informe seus valores reais via flags (--separation, --recruitment, etc.).")


# ========== Batch mode ==========


BATCH_FIELDS_OUT = [
    "role_label", "annual_salary", "level",
    "separation", "recruitment", "training",
    "productivity_loss", "team_impact", "knowledge_loss", "customer_impact", "rework",
    "total_cost", "pct_of_salary",
]


def _f(row: dict, key: str, default: float | None = None) -> float | None:
    v = row.get(key, "")
    if v is None or str(v).strip() == "":
        return default
    try:
        return float(v)
    except ValueError:
        return default


def batch_process(input_path: Path, output_path: Path) -> tuple[int, int]:
    rows_out = []
    ok = fail = 0
    with input_path.open(newline="", encoding="utf-8-sig") as fin:
        reader = csv.DictReader(fin)
        for row in reader:
            try:
                salary = _f(row, "annual_salary")
                if not salary or salary <= 0:
                    fail += 1
                    continue
                level = (row.get("level") or "specialist").strip().lower()
                if level not in LEVEL_MULTIPLIERS:
                    level = "specialist"
                inp = Inputs(
                    annual_salary=salary,
                    level=level,
                    separation=_f(row, "separation"),
                    recruitment=_f(row, "recruitment"),
                    training=_f(row, "training"),
                    ramp_months=_f(row, "ramp_months", 6.0) or 6.0,
                    ramp_productivity_gap=_f(row, "ramp_productivity_gap", 0.5) or 0.5,
                    team_impact=_f(row, "team_impact"),
                    knowledge_loss=_f(row, "knowledge_loss"),
                    customer_impact=_f(row, "customer_impact"),
                    rework=_f(row, "rework"),
                    role_label=(row.get("role_label") or "").strip(),
                )
                r = calcular(inp)
                rows_out.append({
                    "role_label": inp.role_label,
                    "annual_salary": inp.annual_salary,
                    "level": inp.level,
                    "separation":      next(c.value for c in r.components if c.name == "separation"),
                    "recruitment":     next(c.value for c in r.components if c.name == "recruitment"),
                    "training":        next(c.value for c in r.components if c.name == "training"),
                    "productivity_loss": next(c.value for c in r.components if c.name == "productivity"),
                    "team_impact":     next(c.value for c in r.components if c.name == "team_impact"),
                    "knowledge_loss":  next(c.value for c in r.components if c.name == "knowledge_loss"),
                    "customer_impact": next(c.value for c in r.components if c.name == "customer_impact"),
                    "rework":          next(c.value for c in r.components if c.name == "rework"),
                    "total_cost":      r.total,
                    "pct_of_salary":   r.pct_of_salary,
                })
                ok += 1
            except Exception:
                fail += 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=BATCH_FIELDS_OUT)
        writer.writeheader()
        for r in rows_out:
            writer.writerow(r)
    return ok, fail


# ========== CLI ==========


def main() -> int:
    p = argparse.ArgumentParser(
        description="Calculadora do custo real de turnover (Brasil). Metodologia: artigo Cajuína 'O custo oculto do turnover'.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--annual-salary", type=float, help="Salário anual (R$). Obrigatório em modo single.")
    p.add_argument("--level", default="specialist", choices=list(LEVEL_MULTIPLIERS.keys()),
                   help="Nível do cargo. Define o multiplicador de referência.")
    p.add_argument("--role-label", default="", help="Label opcional (ex: 'Eng Manager') pra aparecer no output.")
    p.add_argument("--quick", action="store_true",
                   help="Modo rápido: estima todos os componentes a partir do multiplicador. Não exige --separation etc.")

    # Detailed component overrides
    p.add_argument("--separation",      type=float, help="Custo de separação (rescisão + jurídico)")
    p.add_argument("--recruitment",     type=float, help="Custo de recrutamento (posting + recruiter + tempo gestor)")
    p.add_argument("--training",        type=float, help="Custo de onboarding e treinamento")
    p.add_argument("--ramp-months",     type=float, default=6.0, help="Meses até produtividade plena (default 6)")
    p.add_argument("--ramp-productivity-gap", type=float, default=0.5, help="Gap médio de produtividade no ramp (0-1, default 0.5)")
    p.add_argument("--team-impact",     type=float, help="Custo do impacto no time (moral, sobrecarga)")
    p.add_argument("--knowledge-loss",  type=float, help="Custo da perda de conhecimento/expertise")
    p.add_argument("--customer-impact", type=float, help="Custo de impacto em cliente (cargos client-facing)")
    p.add_argument("--rework",          type=float, help="Custo de erros e retrabalho")

    # Batch
    p.add_argument("--input",  type=Path, help="CSV de desligamentos pra batch mode (colunas: role_label, annual_salary, level, separation, recruitment, training, ramp_months, ramp_productivity_gap, team_impact, knowledge_loss, customer_impact, rework)")
    p.add_argument("--output", type=Path, help="CSV de saída pro batch mode (default: ./turnover-cost-{timestamp}.csv)")

    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    # Batch
    if args.input:
        if not args.output:
            from datetime import datetime
            args.output = Path.cwd() / f"turnover-cost-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
        ok, fail = batch_process(args.input, args.output)
        print(f"Processado {ok + fail} linhas — {ok} ok, {fail} falhas.")
        print(f"Output: {args.output}")
    else:
        if not args.annual_salary:
            p.error("--annual-salary é obrigatório (ou use --input para modo batch).")
        inp = Inputs(
            annual_salary=args.annual_salary,
            level=args.level,
            role_label=args.role_label,
            separation=args.separation,
            recruitment=args.recruitment,
            training=args.training,
            ramp_months=args.ramp_months,
            ramp_productivity_gap=args.ramp_productivity_gap,
            team_impact=args.team_impact,
            knowledge_loss=args.knowledge_loss,
            customer_impact=args.customer_impact,
            rework=args.rework,
        )
        r = calcular(inp)
        print_result(r)

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=custo-turnover-calculator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
