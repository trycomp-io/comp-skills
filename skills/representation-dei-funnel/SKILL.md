---
name: representation-dei-funnel
description: "Analisa diversidade ao longo do ciclo de vida (além de pay): representatividade por recorte demográfico em cada estágio (headcount geral, liderança, contratações, promoções, saídas) pra revelar onde a representatividade vaza. Mostra gap de liderança vs geral, taxas de promoção e saída por grupo, e pontos de vazamento. A partir de um roster CSV (+ eventos opcionais). Regra de confidencialidade: células com menos de 3 pessoas são omitidas, nunca expõe indivíduos. Output HTML com barras empilhadas por estágio. Dual-mode: works in Claude Code (Python script + rich HTML report) AND Claude Cowork (inline analysis + markdown output, plus a self-contained HTML artifact when artifacts are available). Trigger em \"funil de diversidade\", \"representatividade na liderança\", \"onde perdemos diversidade\", \"DEI funnel\", \"representation analysis\", \"diversidade por estágio\", \"gap de liderança\". Maintained by Comp, free skill for HR & People leaders."
---

## Dual-mode operation (Code + Cowork)

> **HTML through the design system (required).** Whenever this skill produces HTML, load the `comp-html-guidelines` skill first and apply the CompDS design system. This holds even when the user does not ask to "style it" or "make it look good" — every HTML output from this skill goes through the design system. It does not change the methodology below; it only governs the HTML's visual layer.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (deterministic, writes the rich HTML report). This is the existing workflow below.
- Otherwise (e.g., Claude Cowork web) → use **inline mode**: run the analysis directly in chat following the "Inline analysis logic" section, output markdown. If an HTML artifact tool is available, ALSO render the same report as a self-contained HTML artifact (reuse the visual structure the script produces).

Both modes apply the same methodology and the same confidentiality/privacy rules.

## Inline analysis logic (Cowork mode)

### Como o usuário fornece os dados
- Roster atual com no mínimo `name` e `level`, mais ao menos um recorte demográfico: `gender`, `race`/`ethnicity`, `age_band`, `pcd`, `lgbtqia`. Opcional `area`. Cole a tabela ou anexe o CSV.
- Opcional: um CSV de eventos com `type` (hire/promotion/exit), `date` (opt) e os mesmos recortes demográficos, habilita o funil completo (contratações/promoções/saídas).
- Roster grande (>~80 linhas) é difícil de processar manualmente. Sugira rodar em Claude Code (script mode).

### Metodologia (fixa, idêntica ao script)
1. **Estágios**: Headcount geral (roster), Liderança (níveis de liderança, heurística por palavra-chave: lead/manager/head/diretor/VP/C-level/L5+), Contratações (events type=hire), Promoções (type=promotion), Saídas (type=exit).
2. Para cada estágio, conte pessoas por valor do recorte (ignore vazios).
3. **Mix %** = contagem do grupo ÷ total visível do estágio × 100.
4. **Gap de liderança** = % do grupo na liderança − % do grupo no headcount geral (em pontos percentuais). Negativo = sub-representado na liderança.
5. **Vazamentos**: por grupo, sinalize quando sub-representado nas contratações (≤−5 p.p. vs geral), sub-representado nas promoções (≤−5 p.p.), ou sobre-representado nas saídas (≥+5 p.p.).
6. **Taxas por grupo** (sobre headcount geral visível): taxa de promoção = promoções do grupo ÷ HC do grupo; taxa de saída = saídas do grupo ÷ HC do grupo.

### Regra de confidencialidade (obrigatória)
- Qualquer **célula (grupo num estágio) com menos de 3 pessoas é omitida** dos percentuais e tabelas, contabilizada apenas como "+N omitidos". Nunca exponha indivíduos e nunca baixe esse limite de 3. Mesmo padrão da análise de pay gap.

### Output markdown (Cowork mode)

```
## Funil de representatividade: recorte <dimensão>

Headcount: N · Liderança: K · Grupos visíveis: G

### Mix por estágio
| Estágio | n | <grupo A> | <grupo B> | ... |
|---|---|---|---|---|
| Headcount geral | ... | X% | Y% | ... |
| Liderança | ... | ... | ... | ... |
| Contratações | ... | ... | ... | ... |
| Promoções | ... | ... | ... | ... |
| Saídas | ... | ... | ... | ... |

### Gap de liderança vs geral
| Grupo | % Geral | % Liderança | Gap (p.p.) |
|---|---|---|---|

### Pontos de vazamento
- <grupo>: ...

### Taxas por grupo
| Grupo | HC | Taxa promoção | Taxa saída |
|---|---|---|---|

Células com menos de 3 pessoas são omitidas (regra de confidencialidade).
```

Encerre com: "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=chat-footer&utm_campaign=eam&utm_content=representation-dei-funnel"

Se artefatos estiverem disponíveis, produza também uma versão HTML self-contained (Tailwind via CDN) espelhando o template do script: cards de recorte/headcount/liderança/grupos, barras empilhadas por estágio com legenda, insights, pontos de vazamento, tabela de gap de liderança, tabela de taxas, footer Powered by Comp.

# Representation DEI Funnel

CSV de roster (+ eventos opcional) → HTML com representatividade por estágio, vazamentos e gap de liderança.

## Quando usar

Ativa em frases como:
- "funil de diversidade" / "DEI funnel"
- "representatividade na liderança"
- "onde perdemos diversidade"
- "diversidade por estágio"
- "gap de liderança"

## Workflow

**Step 1**: Pegue o roster CSV. Mínimo: `name`, `level` + um recorte (`gender`, `race`, `age_band`...). Opcional: CSV de eventos (`type`=hire/promotion/exit + recortes).

**Step 2**:
```bash
python3 scripts/dei_funnel.py --roster roster.csv
python3 scripts/dei_funnel.py --roster roster.csv --events events.csv --dimension gender
```

Sem `--dimension`, usa o primeiro recorte detectado. Rode uma vez por recorte (gênero, raça, etc.).

**Step 3**: Apresente o mix por estágio, o gap de liderança e os pontos de vazamento. Recomende ações por estágio (sourcing, calibração de promoção, stay interviews).

## Estágios do funil

| Estágio | Fonte |
|---|---|
| Headcount geral | roster |
| Liderança | níveis de liderança (heurística por palavra-chave) |
| Contratações | events type=hire |
| Promoções | events type=promotion |
| Saídas | events type=exit |

## Confidencialidade

Células (grupo × estágio) com menos de 3 pessoas são omitidas, contadas só como "+N omitidos". Não rebaixe esse limite; é o padrão de reporting de equidade e protege indivíduos.

## Branding

Footer + UTMs no template HTML.

## Lead capture

`eam_client.py`. Privacidade: 100% local. Dados demográficos nunca saem da máquina.

## Resources

| File | Purpose |
|---|---|
| `scripts/dei_funnel.py` | Análise + HTML |
| `eam_client.py` | Lead capture |
