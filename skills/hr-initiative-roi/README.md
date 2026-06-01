# hr-initiative-roi

Skill gratuito do Claude para líderes de RH & People. Constrói o **business case financeiro** de uma iniciativa de People (custos vs benefícios) pra ganhar buy-in de CFO/CEO. Devolve ROI%, payback em meses, net benefit acumulado em 3 anos e sensibilidade.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=hr-initiative-roi)).

## O que faz

Transforma uma iniciativa de RH em um caso de negócio defensável:

- **Custos**: one-time + recorrente anual
- **Benefícios quantificados** (uma ou mais linhas):
  - Redução de attrition: `Δattrition × headcount × custo por turnover`
  - Ganho de produtividade: `% ganho × headcount × custo carregado`
  - Redução de time-to-fill: `dias economizados × custo/dia de vaga × contratações/ano`
  - Linha custom: rótulo + valor anual
- **Headline**: ROI% (ano 1) + payback em meses + net benefit acumulado em 3 anos
- **Sensibilidade**: Conservador (×0,6) · Esperado (×1,0) · Otimista (×1,3)
- **Visão visual**: barras custo vs benefício com marcador de payback, tabela de sensibilidade (HTML no Code)

Casos de uso:
- Defender um programa de retenção / L&D / wellbeing com o CFO
- Justificar a compra de uma ferramenta de recrutamento
- Comparar iniciativas concorrentes por ROI e payback

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Faz o business case de um programa de retenção: custa R$ 150K + R$ 200K/ano, reduz attrition em 4pp em 120 pessoas"
"Vale a pena essa ferramenta de recrutamento? Reduz time-to-fill em 15 dias, 30 contratações/ano"
"Qual o ROI e payback de um programa de L&D pra 80 pessoas?"
```

## Dual-platform

Funciona em **Claude Code** (script Python + HTML visual com custo vs benefício e sensibilidade) e **Claude Cowork** (cálculo inline + markdown, com artefato HTML quando disponível).

## Modelo

- Benefício anual = soma das linhas quantificadas
- ROI ano 1 = (benefício − custo total) ÷ custo total
- Payback = custo total ÷ benefício mensal líquido de custo recorrente
- 3 anos: ano 1 carrega o one-time, anos 2-3 só recorrente
- Sensibilidade por multiplicador sobre o benefício

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia custos, benefícios ou premissas.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
