# Default Cadences: CHRO

Cadências padrão de um CHRO em empresa Series A-C / growth-stage. O skill assume isso quando o CHRO não customiza explicitamente.

## Semanal
- **1:1 CEO**: alinhamento + asks + people pulse
- **1:1 com diretos** (heads de TA, L&D, comp, ops, people analytics)
- **ELT meeting** (semanal ou quinzenal, varia por empresa)
- **People leadership team meeting** (CHRO + diretos)

## Mensal
- **People update pro CEO** (1-pager), usa `ceo-people-update-drafter`
- **Skip-level com manager-of-managers** (rotacional)
- **Talent review pipeline check** (sucessão, bench, flight risk)
- **Operational review** (headcount, custo folha, vagas abertas)

## Trimestral
- **Board people slide**, usa `board-people-slide-builder`
- **Comp committee** (se aplicável), usa `comp-budget-defense-pack`
- **Engagement pulse**, usa `engagement-deep-dive`
- **Quarterly OKR review**
- **ELT offsite prep**

## Semestral
- **Comp cycle** (review + merit): kick-off + execução + comunicação
- **Workforce planning** (alinhado com FY budget)
- **Performance calibration mid-cycle**

## Anual
- **Performance cycle** (full review + promotion + comp)
- **Annual budget** (headcount + comp)
- **Board annual review** (governance, sucessão, leadership development)
- **Employee survey major** (deep dive de cultura)

## Eventos / triggers ad-hoc
- **Hire de liderança** → kick-off + onboarding plan (usa `onboarding-kit-generator`)
- **Saída de liderança** → comunicação + transição + replacement plan
- **Reorg** → decision memo + change management + comunicação (usa `decision-memo-generator`)
- **Dissídio sindical** → impact analysis (usa `reajuste-impact-calculator`)
- **Pay equity audit** → análise (usa `paygap-analysis-generator` + `comp-ratio-analyzer` + `promotion-equity-analyzer`)

## Como o skill usa essas cadências

Quando o CHRO chama `week` ou `prompt`, o skill:
1. Lê hoje e a data dos próximos eventos no calendário (config)
2. Cruza com as cadências pra inferir o que deveria estar acontecendo
3. Sugere prep, comunicações pendentes, análises a rodar
4. Recomenda os sub-skills relevantes

Exemplo: "comp cycle começa em 4 semanas" → "deveria estar finalizando philosophy, calibrando matriz, alinhando com CFO o budget. Roda `comp-budget-defense-pack` quando tiver os números."
