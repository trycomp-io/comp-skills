# comp-ratio-analyzer

Skill gratuito do Claude para CHROs/Comp partners. Analisa compa-ratio (posicionamento salarial vs bandas) e devolve distribuição, outliers e custo pra equalizar.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-comp-ratio-analyzer)).

## O que faz

Você sobe 2 CSVs (roster + bandas). Skill devolve HTML com:
- Distribuição (% under/at/over)
- Custo mensal pra equalizar todos abaixo da mediana (+ anual com encargos)
- Top 10 outliers por direção (under e over)
- Compa-ratio médio/min/max por nível

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Analisa o compa ratio do meu time. Tenho o roster e a tabela de bandas."
"Quanto custa equalizar todos os under-paid?"
"Outliers salariais: quem precisa de revisão?"
```

## CSVs necessários

**Roster** (mínimo): `name`, `salary`, `level`. Opcional: `area`.

**Bands** (mínimo): `level`, `mid` (mediana). Opcional: `min`, `max`.

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia roster, salários ou bandas.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
