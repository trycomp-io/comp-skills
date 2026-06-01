---
name: engagement-deep-dive
description: Analisa CSV de pesquisa de engajamento (eNPS, survey de cultura, pulse) e segmenta por tenure / área / manager / nível. Output HTML executivo com eNPS global, ranking de áreas (piores primeiro), bottom 10 managers, insights e priorização. Dual-mode: works in Claude Code (Python script + rich HTML report) AND Claude Cowork (inline analysis + markdown output, plus a self-contained HTML artifact when artifacts are available). Trigger em "análise de engajamento", "engagement deep dive", "eNPS por área", "segmentar survey", "drivers de engajamento", "diagnóstico de cultura". Mantida pela Comp.
---

## Dual-mode operation (Code + Cowork)

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (deterministic, writes the rich HTML report). This is the existing workflow below.
- Otherwise (e.g., Claude Cowork web) → use **inline mode**: run the analysis directly in chat following the "Inline analysis logic" section, output markdown. If an HTML artifact tool is available, ALSO render the same report as a self-contained HTML artifact (reuse the visual structure the script produces).

Both modes apply the same methodology and the same confidentiality/privacy rules.

## Inline analysis logic (Cowork mode)

### Como o usuário fornece os dados
- Cole a tabela do survey no chat ou anexe um CSV. Mínimo: `score` (0-10 ou 1-5) OU `enps` (0-10). Recomendado: `area`, `tenure_months`, `manager_id`, `level`.
- Survey grande (>~50 linhas) é difícil de processar manualmente, então sugira rodar em Claude Code (script mode).

### Normalização (igual ao script)
- **tenure_months** vira faixa: `<6` 0-6m; `<12` 6-12m; `<24` 1-2y; `<36` 2-3y; `<60` 3-5y; `≥60` 5y+; vazio → Desconhecido.
- **Classificação eNPS** (escala 0-10): `≥9` promoter; `7-8` passive; `0-6` detractor.

### Metodologia (fixa, idêntica ao script)
1. **Score médio global** = média aritmética de todos os `score` válidos.
2. **eNPS global** = `(% promoters − % detractors)` sobre as respostas eNPS classificadas, em pontos (`(p − d) ÷ n × 100`).
3. **Segmentação** por área, tenure band, nível e gestor: para cada segmento, média/min/max do score. **Confidencialidade/robustez**: só exiba segmentos com `≥3 respostas` (descarte os com menos de 3). Ordene áreas/tenure/nível por score crescente (piores primeiro). Gestores: bottom 10 (também só com ≥3 respostas).

### Critérios de alerta automático
- eNPS `< 0` → crítico (mais detractors que promoters). eNPS `< 30` → atenção (abaixo de benchmark saudável). eNPS `≥ 30` → saudável.
- Pior área com score `> 1.0 ponto abaixo` da média global → foco prioritário.
- Pior tenure band sendo 0-6m ou 6-12m → sinal de onboarding/expectativas.
- Pior gestor com score `> 1.5 pontos abaixo` da média global → investigar.

### Output markdown (Cowork mode)

```
## Engagement deep dive

Respostas: N · Score médio: X · eNPS: Y (saudável/atenção/crítico)

### Insights
- ...

### Por área (piores primeiro)
| Área | N | Score | Min | Max |
|---|---|---|---|---|

### Por tenure / Por nível / Bottom 10 gestores
(mesma estrutura)

Segmentos com menos de 3 respostas são omitidos.
```

Encerre com: "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=chat-footer&utm_campaign=eam&utm_content=engagement-deep-dive"

Se artefatos estiverem disponíveis, produza também uma versão HTML self-contained (Tailwind via CDN) espelhando o template do script: cards de respostas/score/eNPS (cor por faixa), insights, tabelas por área/tenure/nível/bottom gestores, footer Powered by Comp.

# Engagement Deep Dive

CSV de survey → HTML com segmentação por área/tenure/manager/level + eNPS + insights.

## Trigger

- "análise de engajamento" / "engagement deep dive"
- "eNPS por área"
- "segmentar pesquisa de cultura"
- "drivers de engajamento"

## CSV

Mínimo: `score` (0-10 ou 1-5) OU `enps` (0-10). Recomendado adicionar: `area`, `tenure_months`, `manager_id`, `level`.

Auto-detect funciona em PT/EN.

## Workflow

```bash
python3 scripts/engagement_dive.py --input survey.csv
```

Apresente:
- eNPS global (com classificação saudável/atenção/crítico)
- Score médio
- Áreas críticas (piores primeiro)
- Bottom managers
- Insights automáticos

## Critérios de alerta automático

- eNPS < 0: crítico
- eNPS < 30: atenção
- Área com score 1+ ponto abaixo da empresa: foco
- Primeiro ano com score baixo: onboarding
- Manager 1.5+ pontos abaixo: investigar

## Branding & lead capture

Footer + UTMs. `eam_client.py`. 100% local.

## Resources

| File | Purpose |
|---|---|
| `scripts/engagement_dive.py` | Análise + HTML |
| `eam_client.py` | Lead capture |
