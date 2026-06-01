# recruiting-funnel-analytics

Skill gratuito do Claude para CHROs/People leaders e times de Talent Acquisition. Mede a efetividade do recrutamento a partir do pipeline de candidatos.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=recruiting-funnel-analytics)).

## O que faz

Você sobe um CSV de pipeline. Skill devolve HTML com:
- Funil de conversão estágio-a-estágio (applied→screen→interview→offer→hire) com pass-through %
- Gargalo (estágio de menor pass-through)
- Time-to-fill (média e mediana, se houver datas)
- Taxa de aceite de oferta + motivos de recusa
- Efetividade por fonte (volume, hires, conversão)

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Analisa o funil do meu recrutamento."
"Onde os candidatos mais desistem?"
"Qual fonte traz os melhores hires? E o time-to-fill?"
```

## CSV necessário

**Pipeline** (uma linha por candidato). Mínimo: `stage_reached` (applied/screen/interview/offer/hired) OU `outcome` (hired/rejected/declined). Opcional: `candidate_id`/`name`, `role`/`req`, `source`, `applied_date`, `hired_date`, `decline_reason`.

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia o pipeline nem dados de candidatos.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
