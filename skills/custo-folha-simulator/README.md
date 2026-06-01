# custo-folha-simulator

Skill gratuito do Claude para líderes de RH & People brasileiros. Simulador de custo TOTAL empregador de folha de pagamento (salários + encargos + provisões + benefícios).

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-custo-folha-simulator)).

## O que faz

Em segundos, calcula:
- Encargos patronais (~35.8%): INSS 20%, FGTS 8%, SAT 2%, Sistema S 5.8%
- Provisões (~19.7%): 13º + férias + 1/3 + multa FGTS
- Custo mensal e anual total
- Onerated factor (custo / salário bruto)
- Breakdown por área (se CSV)

**Não substitui sistema de folha real**: serve pra orçamento, projeção, cenários "e se".

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Quanto vai custar minha folha mensal com 50 pessoas a R$ 8k médio?"
"Calcula o custo total da folha desse roster" (+ CSV)
"Projeção de folha pro próximo ano com headcount X"
```

## Modos

| Modo | Como invocar |
|---|---|
| Detailed (CSV) | `python3 scripts/custo_folha.py --input roster.csv` |
| Estimate | `python3 scripts/custo_folha.py --headcount 50 --salario-medio 8000` |

## O que está coberto

- Encargos patronais BR (INSS, FGTS, SAT, Sistema S)
- Provisões legais (13º, férias + 1/3, multa FGTS rescisória)
- Benefícios (VR/VA + outros)

## O que NÃO está coberto

- Folha real (use seu HRIS)
- INSS/IRPF do colaborador (descontos, não custos)
- Variações de Sistema S por setor
- Benefícios com incidência tributária complexa (plano saúde como in natura, etc.)

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia salários ou roster.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
