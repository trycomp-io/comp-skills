# reajuste-impact-calculator

Skill gratuito do Claude para líderes de RH & People. Calcula impacto financeiro completo de reajuste salarial (dissídio, mérito, ajustes pontuais) incluindo encargos.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-reajuste-impact-calculator)).

## O que faz

Você dá um roster + regra de reajuste. Recebe:
- ∆ total mensal (só salários)
- ∆ total mensal **com encargos** (~55.5% adicional)
- ∆ anual com encargos
- % impacto na folha bruta
- Breakdown por grupo

Diferencia regras por nível, por área, ou flat (todos iguais).

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Quanto custa um dissídio de 5% na folha?"
"Simula um ciclo de mérito: Junior 8%, Pleno 5%, Senior 4%, Manager 3%"
"Reajuste só pra Eng de 6%, qual o impacto?"
```

## Tipos de regra

| Modo | Comando |
|---|---|
| Flat (todos iguais) | `--flat 5` |
| Por nível | `--rule-by level --rules '{"Junior":8,"Pleno":5}'` |
| Por área | `--rule-by area --rules '{"Eng":5,"Sales":4}'` |

## Por que isso importa

CHROs frequentemente comunicam "vamos dar 5% de aumento" e o CFO pergunta "quanto isso vai custar?". A resposta não é 5% da folha, é 5% × 1.555 (porque tem encargos + provisões). O skill traz esse número anualizado pronto pra defesa.

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia salários ou roster.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
