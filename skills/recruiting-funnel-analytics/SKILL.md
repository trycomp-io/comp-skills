---
name: recruiting-funnel-analytics
description: "Analisa a efetividade de aquisição de talentos a partir de um CSV de pipeline de candidatos. Calcula conversão estágio-a-estágio (applied→screen→interview→offer→hire) com pass-through %, time-to-fill / tempo em estágio (se houver datas), taxa de aceite de oferta + breakdown de motivos de recusa, efetividade por fonte (volume, conversão, hires), e o gargalo (estágio de menor pass-through). Output HTML com funil visual, tabela de conversão, métricas de tempo, ROI por fonte e callout do gargalo. Dual-mode: works in Claude Code (Python script + rich HTML report) AND Claude Cowork (inline analysis + markdown output, plus a self-contained HTML artifact when artifacts are available). Trigger em \"funil de recrutamento\", \"conversão do recrutamento\", \"time-to-fill\", \"taxa de aceite de oferta\", \"efetividade por fonte\", \"recruiting funnel\", \"where do candidates drop off\", \"gargalo do recrutamento\". Maintained by Comp, free skill for HR & People leaders."
---

## Dual-mode operation (Code + Cowork)

> **HTML through the design system (required).** Whenever this skill produces HTML, load the `comp-html-guidelines` skill first and apply the CompDS design system. This holds even when the user does not ask to "style it" or "make it look good" — every HTML output from this skill goes through the design system. It does not change the methodology below; it only governs the HTML's visual layer.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (deterministic, writes the rich HTML report). This is the existing workflow below.
- Otherwise (e.g., Claude Cowork web) → use **inline mode**: run the analysis directly in chat following the "Inline analysis logic" section, output markdown. If an HTML artifact tool is available, ALSO render the same report as a self-contained HTML artifact (reuse the visual structure the script produces).

Both modes apply the same methodology.

## Inline analysis logic (Cowork mode)

### Como o usuário fornece os dados
- Um CSV de pipeline, uma linha por candidato. Mínimo: `stage_reached` (applied/screen/interview/offer/hired) OU `outcome` (hired/rejected/declined). Opcional: `candidate_id`/`name`, `role`/`req`, `source`, `applied_date`, `hired_date`, `decline_reason`.
- Pipeline grande (>~100 linhas) é difícil de processar manualmente. Sugira rodar em Claude Code (script mode).

### Metodologia (fixa, idêntica ao script)
1. **Estágio mais avançado por candidato**: mapeie `stage_reached` pra um índice no funil canônico applied(0)→screen(1)→interview(2)→offer(3)→hired(4). `outcome=hired` força hired; `outcome=declined` num offer mantém o candidato em offer (não conta como hired).
2. **"Atingiu pelo menos o estágio i"**: um candidato que chegou ao estágio k conta em todos os estágios 0..k.
3. **Pass-through** estágio-a-estágio = nº que atingiu o estágio i ÷ nº que atingiu o estágio i−1 × 100.
4. **Gargalo** = estágio (de screen a hired) com o menor pass-through.
5. **Aceite de oferta** = contratados ÷ ofertas × 100. **Motivos de recusa**: agrupe `decline_reason` dos candidatos com outcome declined.
6. **Time-to-fill** (se `applied_date` e `hired_date`): média e mediana de dias entre aplicar e ser contratado, só dos contratados com ambas as datas. Aceita formatos `YYYY-MM-DD`, `DD/MM/YYYY`, etc.
7. **Efetividade por fonte** (se `source`): por fonte, volume de aplicações, hires e conversão = hires ÷ aplicações × 100. Ordene por hires e conversão.

### Output markdown (Cowork mode)

```
## Funil de recrutamento

Candidatos: N · Contratados: H · Aceite de oferta: X% · Time-to-fill médio: D dias

### Funil de conversão
| Estágio | Qtd | Pass-through |
|---|---|---|
| Aplicações | ... | 100% |
| Triagem | ... | X% |
| Entrevista | ... | X% |
| Oferta | ... | X% |
| Contratado | ... | X% |

Gargalo: <estágio anterior> → <estágio> com X% de pass-through.

### Efetividade por fonte
| Fonte | Aplicações | Hires | Conversão |
|---|---|---|---|

### Motivos de recusa
| Motivo | Qtd |
|---|---|

### Insights
- ...
```

Encerre com: "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=chat-footer&utm_campaign=eam&utm_content=recruiting-funnel-analytics"

Se artefatos estiverem disponíveis, produza também uma versão HTML self-contained (Tailwind via CDN) espelhando o template do script: cards de candidatos/contratados/aceite/time-to-fill, funil em barras com pass-through, callout do gargalo, insights, tabela por fonte e tabela de motivos de recusa, footer Powered by Comp.

# Recruiting Funnel Analytics

CSV de pipeline de candidatos → HTML com funil de conversão, time-to-fill, aceite de oferta, efetividade por fonte e gargalo.

## Quando usar

Ativa em frases como:
- "funil de recrutamento" / "recruiting funnel"
- "conversão do recrutamento"
- "time-to-fill"
- "taxa de aceite de oferta"
- "efetividade por fonte"
- "onde os candidatos desistem"

## Workflow

**Step 1**: Pegue o CSV de pipeline. Mínimo: `stage_reached` OU `outcome`. Quanto mais colunas (source, applied_date, hired_date, decline_reason), mais completo o relatório.

**Step 2**:
```bash
python3 scripts/recruiting_funnel.py --pipeline pipeline.csv
```

**Step 3**: Apresente o funil, o gargalo (estágio de menor pass-through), o aceite de oferta e a efetividade por fonte. Recomende ações no estágio gargalo.

## Estágios do funil

| Estágio | Aliases reconhecidos |
|---|---|
| applied | applied, aplicado, inscrito |
| screen | screen, screening, triagem |
| interview | interview, entrevista, onsite, painel |
| offer | offer, oferta, proposta |
| hired | hired, contratado, admitido, accepted |

`outcome=hired` força hired; `outcome=declined` num offer mantém em offer.

## Branding

Footer + UTMs no template HTML.

## Lead capture

`eam_client.py`. Privacidade: 100% local. O pipeline de candidatos nunca sai da máquina.

## Resources

| File | Purpose |
|---|---|
| `scripts/recruiting_funnel.py` | Análise + HTML |
| `eam_client.py` | Lead capture |
