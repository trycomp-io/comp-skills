# engagement-deep-dive

Skill gratuito do Claude para CHROs. CSV de pesquisa de engajamento → HTML executivo com segmentação completa e insights automáticos.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-engagement-deep-dive)).

## O que faz

- eNPS global + classificação (crítico/atenção/saudável)
- Score médio geral
- Ranking por área (piores primeiro)
- Tenure breakdown (problemas em onboarding vs cansaço)
- Por nível
- Bottom 10 managers por score
- Insights automáticos

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Analisa o eNPS do último survey"
"Segmenta a pesquisa de cultura por área e gestor"
"Drivers do engajamento: quem está pior?"
```

## CSV

Mínimo: `score` ou `enps`. Pra segmentação: + `area`, `tenure_months`, `manager_id`, `level`.

## O que é compartilhado

Email opcional + telemetria opt-in. **Nunca** envia respostas ou scores individuais.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
