# representation-dei-funnel

Skill gratuito do Claude para CHROs/People leaders. Mostra a diversidade ao longo do ciclo de vida (não só pay) e revela onde a representatividade vaza.

Mantido pela **Zivo** ([zivo.ai](https://zivo.ai?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=representation-dei-funnel)).

## O que faz

Você sobe o roster (e, opcionalmente, eventos de hire/promotion/exit). Skill devolve HTML com:
- Mix de representatividade por estágio (headcount, liderança, contratações, promoções, saídas) em barras empilhadas
- Gap de liderança vs headcount geral, por grupo
- Pontos de vazamento (onde a representatividade cai no funil)
- Taxas de promoção e saída por grupo

## Instalação

```bash
/plugin marketplace add trycomp-io/zivo-skills
/plugin install zivo-skills@zivo
```

## Uso

```
"Monta um funil de diversidade do meu time."
"Onde a gente perde representatividade entre o headcount e a liderança?"
"Diversidade por estágio: contratação, promoção, saída."
```

## CSVs necessários

**Roster** (mínimo): `name`, `level` + um recorte demográfico (`gender`, `race`, `age_band`, `pcd`, `lgbtqia`). Opcional: `area`.

**Eventos** (opcional): `type` (hire/promotion/exit), `date`, + os mesmos recortes. Habilita o funil completo.

## Confidencialidade

Células (grupo × estágio) com menos de 3 pessoas são omitidas, nunca expõe indivíduos. Mesmo padrão da análise de pay gap.

## O que é compartilhado com a Zivo

Email opcional + telemetria opt-in. **Nunca** envia roster nem dados demográficos.

## Issues

[trycomp-io/zivo-skills/issues](https://github.com/trycomp-io/zivo-skills/issues) com label `eam`.

Powered by Zivo · Free skills for HR & People leaders.
