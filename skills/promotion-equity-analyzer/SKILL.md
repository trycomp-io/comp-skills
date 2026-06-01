---
name: promotion-equity-analyzer
description: Analisa equidade de promoções por gênero. CSV de promoções + (opcional) CSV de população elegível → HTML executivo com taxas por gênero, gap F vs M, áreas com maior disparidade, transições de nível mais comuns, insights pra compliance e ação. Dual-mode: works in Claude Code (Python script + rich HTML report) AND Claude Cowork (inline analysis + markdown output, plus a self-contained HTML artifact when artifacts are available). Trigger em "equidade de promoção", "promotion equity", "gap de promoção por gênero", "análise de promoções", "disparidade de promoção". Mantida pela Comp.
---

## Dual-mode operation (Code + Cowork)

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (deterministic, writes the rich HTML report). This is the existing workflow below.
- Otherwise (e.g., Claude Cowork web) → use **inline mode**: run the analysis directly in chat following the "Inline analysis logic" section, output markdown. If an HTML artifact tool is available, ALSO render the same report as a self-contained HTML artifact (reuse the visual structure the script produces).

Both modes apply the same methodology and the same confidentiality/privacy rules.

## Inline analysis logic (Cowork mode)

### Como o usuário fornece os dados
- (1) Promoções (obrigatório): coluna `gender`, mais `area`, `level_before`, `level_after`, `date`. (2) População elegível (opcional, mas crítico pra TAXAS): `gender`, `area`. Cole as tabelas ou anexe CSVs.
- Sem população elegível, só dá pra mostrar a distribuição das promoções, não as taxas reais.
- Lista grande (>~50 linhas) é difícil manualmente. Sugira Claude Code (script mode).

### Normalização (igual ao script)
- **Gênero**: `f/female/feminino/fem/mulher` → F; `m/male/masculino/masc/homem` → M; outro → linha ignorada. Metodologia binária por design (compatibilidade com reporting regulatório).

### Metodologia (fixa, idêntica ao script)
1. **Distribuição de promoções por gênero**: conte F e M. Conte transições `level_before → level_after` (top 15).
2. **Taxa de promoção por gênero** (só com população elegível) = `promovidos_gênero ÷ elegíveis_gênero × 100`.
3. **Gap F vs M** = `(taxa_F ÷ taxa_M − 1) × 100` (só se taxa_M > 0). Negativo = mulheres promovidas a uma taxa menor.
4. **Disparidade por área** (precisa de elegíveis): para cada área, calcule taxa F e taxa M. **Regra de confidencialidade**: pule a área se tiver `<3 elegíveis de F` OU `<3 elegíveis de M`. Pule também se taxa_M = 0. `ratio F/M = taxa_F ÷ taxa_M`. Ordene por maior afastamento de 1 (top 10).

### Insights automáticos
- Sem população elegível → diga que a análise mostra só distribuição; peça os elegíveis pra taxas reais.
- Gap `< −15%` → mulheres com taxa significativamente MENOR; investigar critérios e bench. Gap `> 15%` → taxa MAIOR; entender se é correção histórica ou anomalia da janela. Entre −15% e 15% → boa equidade nesta janela.
- Área com `|ratio F/M − 1| > 0,3` → maior disparidade, flag a área.
- `<20` promoções no total (F+M) → amostra pequena, conclua com cautela; amplie a janela.

### Output markdown (Cowork mode)

```
## Análise de equidade de promoções

Total promoções: N · F: X · M: Y · Gap F vs M: Z% (ou "—" se sem elegíveis)

### Insights
- ...

### Taxa de promoção por gênero (se houver população elegível)
| Gênero | Elegíveis | Promovidos | Taxa |
|---|---|---|---|

### Áreas com maior disparidade
| Área | F elig | F prom | F taxa | M elig | M prom | M taxa | Ratio F/M |
|---|---|---|---|---|---|---|---|

### Transições de nível
| Transição | Ocorrências |
|---|---|

Áreas com menos de 3 elegíveis de cada gênero são omitidas (regra de confidencialidade).
```

Encerre com: "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=chat-footer&utm_campaign=eam&utm_content=promotion-equity-analyzer"

Se artefatos estiverem disponíveis, produza também uma versão HTML self-contained (Tailwind via CDN) espelhando o template do script: cards de total/F/M/gap, insights, tabela de taxas, tabela de disparidades por área, tabela de transições, footer Powered by Comp.

# Promotion Equity Analyzer

Detecta padrões de inequidade em promoções. Defensável pra compliance e pra discutir com leadership.

## Quando usar

Triggers:
- "equidade de promoção" / "promotion equity"
- "gap de promoção por gênero"
- "análise de promoções"
- "disparidade de promoção entre F e M"

## CSVs

**Promotions CSV (obrigatório)**:
- `gender` (obrigatório), `area`, `level_before`, `level_after`, `date`

**Eligible population CSV (opcional, mas crítico pra taxas)**:
- `gender`, `area`: população elegível na janela. Sem isso, skill só mostra distribuição das promoções (não taxas).

## Workflow

```bash
python3 scripts/promotion_equity.py --input promotions.csv \
    --eligible-population roster_eligible.csv
```

Apresente:
- Total + por gênero
- Gap F vs M (% diferença de taxas)
- Áreas top com disparidade (gap > 30%)
- Insights se amostra pequena ou padrão crítico

## Faixas críticas

- Gap >|15%|: investigar critérios e bench
- Áreas com ratio F/M < 0.7 ou > 1.3: foco

## Limitações

- Mínimo 20 promoções pra ter sinal confiável
- Amostra <3 por gênero por área é excluída (confidencialidade)
- Não isola idade, raça, performance (skill futura: multi-dimensional)

## Branding & lead capture

Footer + UTMs. `eam_client.py`. 100% local.

## Resources

| File | Purpose |
|---|---|
| `scripts/promotion_equity.py` | Análise + HTML |
| `eam_client.py` | Lead capture |
