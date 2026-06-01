# workforce-headcount-plan

Skill gratuito do Claude para líderes de RH & People. Constrói o **plano de headcount forward-looking** amarrado ao crescimento, projetando quantas pessoas contratar por função por trimestre, o custo incremental de folha, e 3 cenários (Conservador / Base / Agressivo).

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=workforce-headcount-plan)).

## O que faz

Liga o plano de negócio ao plano de pessoas:

- **Driver de crescimento**: receita-alvo (÷ receita por colaborador), % de crescimento, ou headcount-alvo absoluto
- **Projeção por função × trimestre**: headcount necessário, net new hires, custo incremental
- **Backfill por attrition**: separa reposição de saídas do crescimento líquido de capacidade
- **3 cenários**: Conservador (×0,7) · Base (×1,0) · Agressivo (×1,3) sobre o crescimento líquido
- **Headline**: total de contratações líquidas + custo incremental anual (Base)
- **Visão visual**: headcount ao longo do tempo, custo por trimestre, comparação de cenários (HTML no Code)

Casos de uso:
- Planejamento anual de quadro amarrado à meta de receita
- "Quantas pessoas preciso contratar pra dobrar de tamanho, e quanto custa?"
- Stress-test de caixa e capacidade de recrutamento entre cenários

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Monta um plano de headcount pra chegar em R$ 80M de receita, hoje somos 45 pessoas"
"Quantas pessoas preciso contratar por trimestre pra crescer 60% com 12% de attrition?"
"Plano de contratação por função pros próximos 4 trimestres"
```

CSV de funções (opcional, recomendado):

```csv
function,headcount,loaded_cost_annual
Engenharia,18,280000
Produto,6,300000
Vendas,8,240000
Customer Success,5,200000
G&A,8,220000
```

## Dual-platform

Funciona em **Claude Code** (script Python + HTML visual com roadmap e cenários) e **Claude Cowork** (cálculo inline + markdown, com artefato HTML quando disponível).

## Modelo

- Headcount-alvo derivado do driver; crescimento distribuído proporcional ao mix atual
- Interpolação linear até o alvo, trimestre a trimestre
- Net hires = crescimento + backfill (attrition pro-rata)
- Custo carregado ≈ 1,555× salário (encargos + benefícios) quando não informado

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia headcount, custos ou dados do plano.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
