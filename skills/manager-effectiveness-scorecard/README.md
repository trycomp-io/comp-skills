# manager-effectiveness-scorecard

Skill gratuito do Claude para CHROs/People leaders. Cruza sinais de gestão (span, atrito, engajamento, promoção) num score composto 0-100 por gestor, com bandas e flags acionáveis.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=manager-effectiveness-scorecard)).

## O que faz

Você sobe o roster (e, opcionalmente, eventos de saída). Skill devolve HTML com:
- Ranking de gestores (exemplar → at-risk) com score composto transparente
- Scorecard por gestor: span, engajamento médio, atrito, taxa de promoção
- Flags: gestor em risco, sobrecarregado, subutilizado
- Distribuição por banda (At-risk / Developing / Solid / Exemplar)

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Faz um scorecard de eficácia dos meus gestores."
"Quais líderes estão em risco de perder o time?"
"Quais gestores estão sobrecarregados?"
```

## CSVs necessários

**Roster** (mínimo): `name`, `manager`. Opcional: `area`, `engagement_score`, `performance_rating`, `tenure_months`, `promoted_last_cycle`.

**Eventos de saída** (opcional): `manager`, `type` (exit), `regretted`.

## Confidencialidade

Gestores com menos de 3 directs ficam fora de rankings e médias (aparecem marcados como amostra pequena). Protege a privacidade individual dos liderados.

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia roster, engajamento ou saídas.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
