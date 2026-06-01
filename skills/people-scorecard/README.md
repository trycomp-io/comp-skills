# people-scorecard

Skill gratuito do Claude para CHROs/People leaders. A partir de um roster CSV (+ eventos opcional), gera o pacote canônico mensal de People analytics: o scorecard de uma página que você entrega pro CEO.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=people-scorecard)).

## O que faz

Você sobe o roster (e opcionalmente os eventos). A skill devolve um HTML dashboard com:
- Headcount (total, por área, por nível)
- Attrition anualizada (com split lamentável se houver flag)
- Tenure médio + distribuição
- Span of control (médio + distribuição)
- Mobilidade interna (promoções / headcount)
- Representatividade de gênero geral E em liderança (com confidencialidade)
- Taxa de novos contratados / crescimento
- Tendência mensal (se os eventos tiverem datas)

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Monta o people scorecard do mês. Tenho o roster."
"Quais são meus indicadores de RH pro board?"
"Headcount, attrition e tenure do meu time."
```

## CSVs

**Roster** (mínimo `name`): `name`, `area`, `level`, `manager`, `gender`, `tenure_months` ou `hire_date`, `salary`.

**Eventos** (opcional): `type` (hire/exit/promotion), `date`, `regretted`. Sem ele, as taxas (attrition, mobilidade, crescimento) e a tendência são omitidas.

## Regra de confidencialidade

Qualquer grupo de gênero com menos de 3 pessoas é suprimido ("—") e não entra no cálculo de representatividade, protegendo a privacidade individual. Esse limite nunca é reduzido.

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia o roster ou dados individuais.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
