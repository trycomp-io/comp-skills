# total-comp-calculator

Skill gratuito do Claude para líderes de RH & People. Calcula o **Total Compensation** completo, somando cash (base + variável), benefícios e equity (SOP/ILP com cenários de exit), e devolve 2 headline numbers + breakdown + visão visual.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-total-comp-calculator)).

## O que faz

Monta o pacote total de remuneração (não só o salário base):

- **Cash**: base anual (×13,33) + variável/bônus
- **Benefícios**: VR/VA, plano saúde, etc. (mensal × 12)
- **Equity (SOP/ILP)**: ações × strike × pps, com cenários de exit Base 5× / Target 10× / Homerun 30×, anualizado pelo vesting, USD→BRL
- **2 headlines**: near-term (cash + benefícios + variável) e long-term (+ ILP no target)
- **Visão visual**: composição do pacote + tabelas (HTML no Code)

Casos de uso:
- Offer letter: mostrar o valor total do pacote ao candidato
- Conversa de retenção: "você ganha R$ X em salário, mas seu pacote vale R$ Y"
- Comparar 2+ ofertas em base total comp

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Calcula o total comp de alguém com base R$ 12.900, bônus 2.5 salários, ticket + plano de saúde, e 1500 SOPs"
"Quanto vale meu pacote total? Tenho base, bônus e stock options"
"Compara essas duas ofertas em total compensation"
```

## Dual-platform

Funciona em **Claude Code** (script Python + HTML visual com composição) e **Claude Cowork** (cálculo inline + markdown).

## Modelo

- Cash: base × 13,33 (12 + 13º + 1/3 férias) + variável
- Benefícios: mensal × 12
- Equity: cenários de exit anualizados pelo vesting
- Long-term headline usa o cenário target (10×), equity é potencial, não garantia

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia salários, equity ou dados do pacote.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
