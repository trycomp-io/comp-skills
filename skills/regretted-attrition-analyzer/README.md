# regretted-attrition-analyzer

Skill gratuito do Claude para CHROs. Analisa CSV de desligamentos e devolve padrões + insights acionáveis sobre regretted attrition.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-regretted-attrition-analyzer)).

## O que faz

Você sobe CSV de desligamentos. Skill devolve HTML executivo com:
- % regretted vs unregretted (corte primário)
- Top gestores com pattern de regretted
- Áreas hot (turnover acima da média)
- Tenure breakdown (problemas em onboarding vs cansaço de 3+ anos)
- Top performers saindo (sinal crítico)
- Motivos declarados ranqueados
- Insights automáticos com sugestão de ação

Defensável pra CHRO levar pro CEO: não é só número, é narrativa.

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Analisa esse CSV de desligamentos do último ano"
"Por que estamos perdendo gente? Tenho a lista aqui"
"Investigar regretted vs unregretted no time de Eng"
```

## CSV mínimo

Coluna obrigatória: `regretted` (1/0). O resto é opcional: quanto mais colunas, mais segmentação.

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia nomes, dados de desligamento, salários.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
