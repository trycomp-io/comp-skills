# stock-options-calculator

Skill gratuito do Claude para líderes de RH & People em startups/scale-ups. Calcula valor potencial de Stock Options em empresas de capital fechado e devolve cenários de exit + talking points pra conversa com candidato/colaborador.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-stock-options-calculator)).

Baseado no [artigo Comp na Cajuína sobre Stock Options](https://cajuina.org/principais/coluna-comp/stock-options/): a tese de que equity privado compete em multiplicação, não em liquidez.

## O que faz

Modela:
- Vesting timeline (cliff + linear)
- Diluição esperada por rounds até exit
- Cenários de exit (3x, 5x, 10x, 50x, customizável)
- Valor intrínseco hoje (hipotético, sem liquidez)
- Net por opção em cada cenário (depois de strike e diluição)
- Talking points alinhados ao framework

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Calcula o valor de 10.000 opções, strike R$5, FMV R$5, empresa vale R$50M"
"Explica pro meu candidato o vesting de 4 anos com cliff de 1"
"Cenários de exit pra essa SOP: 5x, 10x, 50x"
```

## Limitações

- IR não calculado com precisão (use "Net" como teto otimista)
- Diluição linear (não modela tipos de round)
- Cenários binários (a vida real é Pareto)
- Não substitui consultoria jurídica

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia números do cap table.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
