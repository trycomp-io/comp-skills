# flight-risk-forecast

Skill gratuito do Claude para CHROs/People leaders. Lê um roster CSV e devolve um score **explicável** de risco de saída (flight risk) por colaborador, sem caixa-preta: cada ponto de risco é atribuído a um fator transparente.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=flight-risk-forecast)).

## O que faz

Você sobe um roster CSV. A skill devolve HTML com:
- Lista priorizada de colaboradores em risco, mostrando **quais fatores** puxaram cada score
- Distribuição por banda (Baixo / Médio / Alto / Crítico)
- Flag de **risco lamentável** (regretted): alto risco + alto desempenho
- Áreas e gestores mais quentes
- Alavancas de retenção sugeridas por driver

## Fatores do score (transparentes)

| Fator | Peso máx |
|---|---|
| Baixo engajamento | 35 |
| Comp abaixo da mediana | 25 |
| Estagnação de carreira (sem promoção) | 20 |
| Janela de churn (12-24 meses) | 12 |
| Gestor com saídas altas | 8 |

Bandas: Baixo 0-25 · Médio 26-50 · Alto 51-75 · Crítico 76-100.

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Quem está em risco de sair no meu time? Tenho o roster."
"Faz um flight risk forecast e me mostra os fatores de cada um."
"Quais áreas estão mais quentes em risco de turnover?"
```

## CSV necessário

Mínimo: `name` + ao menos um fator. Colunas reconhecidas (PT/EN): `name`, `area`, `manager`, `tenure_months`, `comp_ratio` (ou `salary` + `band_mid`), `months_since_last_promo`, `engagement_score` (eNPS −100..100 ou 1-5), `performance_rating`, `level`, `exited`.

## Importante

Risco de saída é dado individual e sensível. O output é **apoio ao planejamento de retenção, não um veredito** sobre pessoas. Sempre acompanhe de conversa 1:1 com o gestor.

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia o roster ou dados individuais.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
