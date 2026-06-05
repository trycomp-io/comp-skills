---
name: flight-risk-forecast
description: "Scoring EXPLICÁVEL de risco de saída (flight risk) por colaborador a partir de um roster CSV. Não é caixa-preta: cada ponto de risco é atribuído a um fator transparente (comp abaixo da mediana, estagnação de carreira, baixo engajamento, janela de churn, gestor com saídas altas). Devolve lista priorizada, breakdown por fator, distribuição por banda (Baixo/Médio/Alto/Crítico), flag de risco lamentável (regretted = alto risco + alto desempenho), áreas/gestores mais quentes e alavancas de retenção sugeridas. Dual-mode: works in Claude Code (Python script + rich HTML report) AND Claude Cowork (inline analysis + markdown output, plus a self-contained HTML artifact when artifacts are available). Trigger em \"risco de saída\", \"flight risk\", \"quem está pra sair\", \"previsão de turnover\", \"retention risk\", \"forecast de attrition\", \"quem está em risco de pedir demissão\". Maintained by Comp, free skill for HR & People leaders."
---

## Dual-mode operation (Code + Cowork)

> **HTML through the design system (required).** Whenever this skill produces HTML, load the `comp-html-guidelines` skill first and apply the CompDS design system. This holds even when the user does not ask to "style it" or "make it look good" — every HTML output from this skill goes through the design system. It does not change the methodology below; it only governs the HTML's visual layer.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (deterministic, writes the rich HTML report). This is the existing workflow below.
- Otherwise (e.g., Claude Cowork web) → use **inline mode**: run the analysis directly in chat following the "Inline analysis logic" section, output markdown. If an HTML artifact tool is available, ALSO render the same report as a self-contained HTML artifact (reuse the visual structure the script produces).

Both modes apply the same methodology and the same explainability/privacy rules. Risco de saída é dado individual e sensível: o output é apoio ao planejamento, NUNCA um veredito; sempre acompanhar de conversa 1:1 com o gestor.

## Inline analysis logic (Cowork mode)

### Como o usuário fornece os dados
- Roster com colunas (auto-detect, aliases PT/EN): `name`, `area`, `manager` (opc), `tenure_months`, `comp_ratio` (ou `salary` + `band_mid` pra derivar), `months_since_last_promo` (opc), `engagement_score` (eNPS −100..100 OU 1-5), `performance_rating` (opc, 1-5 ou labels), `level` (opc), `exited` (opc, pra attrition por gestor).
- Cole a tabela no chat ou anexe o CSV. Roster grande (>~50 linhas) é difícil de pontuar manualmente sem erro, então sugira rodar em Claude Code (script mode).
- Precisa de `name` + ao menos UM fator de risco.

### Normalização (igual ao script)
- **engagement**: se valor entre 1 e 5 → escala 1-5, normaliza `(x−1)/4`. Se fora disso (negativo ou >5) → eNPS, normaliza `(x+100)/200`. Resultado 0..1 (1 = ótimo).
- **performance**: aceita 1-5 numérico ou labels (low/baixo=1, below/abaixo=2, meets/atende=3, exceeds/acima=4, outstanding/excepcional=5).
- **comp_ratio**: se ausente mas houver salary + band_mid → `salário ÷ mid`.
- **salário** em formato BR (`.` milhar, `,` decimal) → número.

### Metodologia de scoring (fixa, aditiva, explicável, documente os pesos)
Cada fator soma pontos a um score 0-100. Pesos máximos:

| Fator | Peso máx | Quando soma | Como escala |
|---|---|---|---|
| Comp abaixo do mercado | 25 | comp_ratio < 0,90 | mais abaixo de 0,90 = mais pontos (piso 0,70); ≥1,0 = 0 |
| Estagnação de carreira | 20 | months_since_promo > 24 | satura em 48 meses |
| Baixo engajamento | 35 (maior driver) | engajamento normalizado < 0,5 | quanto mais baixo, mais pontos |
| Janela de churn | 12 | tenure 12-24 meses | pico em ~18 meses |
| Gestor com saídas altas | 8 (só se houver coluna exit) | attrition do gestor > 0 | satura em 30% |

**Bandas**: Baixo (0-25) · Médio (26-50) · Alto (51-75) · Crítico (76-100).
**Risco lamentável (regretted)** = banda Alto/Crítico E performance top-2 (4-5/5).
Attrition é calculado SÓ pra quem ainda está na empresa; linhas marcadas como `exited` alimentam a taxa por gestor mas não são pontuadas.

### Explicabilidade (obrigatório)
Cada pessoa em risco DEVE mostrar quais fatores puxaram o score e quantos pontos cada um somou. Nunca apresente o número sozinho.

### Alavancas de retenção por driver
- Comp abaixo do mercado → revisão salarial / ajuste pra mediana.
- Estagnação de carreira → plano de carreira + conversa de próximo passo.
- Baixo engajamento → 1:1 estruturada, entender driver, plano de ação do gestor.
- Janela de churn → check-in de retenção proativo.
- Gestor com saídas altas → apoio/coaching ao gestor + diagnóstico de clima.

### Output markdown (Cowork mode)

```
## Flight Risk Forecast

Pontuados: N · **Em risco (alto+crítico): X** · Risco lamentável: Y · Score médio: Z

> Apoio ao planejamento, não veredito. Use como gatilho pra conversas 1:1, nunca decisão automática.

### Distribuição
| Baixo | Médio | Alto | Crítico |
|---|---|---|---|

### Colaboradores em risco (com fatores)
| Nome | Área | Gestor | Score | Fatores que pesaram |
|---|---|---|---|---|
| ... | ... | ... | 78 (Crítico) | Baixo engajamento +30; Comp abaixo +15 |

### Áreas / gestores mais quentes
| Área | HC | Score médio | Em risco |
|---|---|---|---|

### Alavancas sugeridas
| Driver | Pessoas afetadas | Alavanca |
|---|---|---|

### Insights
- ...
```

Encerre com: "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=chat-footer&utm_campaign=eam&utm_content=flight-risk-forecast"

Se artefatos estiverem disponíveis, produza também uma versão HTML self-contained (Tailwind via CDN) espelhando o template do script: aviso "apoio ao planejamento", cards de pontuados/em risco/lamentável/score médio, grid de distribuição (4 bandas coloridas), insights, tabela de colaboradores em risco com pills de fatores, áreas/gestores mais quentes, tabela de alavancas, footer Powered by Comp.

# Flight Risk Forecast

Roster CSV → score explicável de risco de saída por colaborador, lista priorizada, áreas/gestores quentes e alavancas de retenção. Output HTML executivo.

## Quando usar

Ativa em frases como:
- "risco de saída" / "flight risk" / "retention risk"
- "quem está pra sair" / "quem está em risco de pedir demissão"
- "previsão de turnover" / "forecast de attrition"

## Workflow

**Step 1**: Pegue o roster CSV. Mínimo: `name` + 1 fator (comp_ratio/salary, engagement, tenure, ou months_since_last_promo).

**Step 2**:
```bash
python3 scripts/flight_risk.py --roster roster.csv
```
O script imprime as colunas detectadas.

**Step 3**: Apresente a lista priorizada com os fatores de cada pessoa (transparência), os números de cabeçalho (em risco / risco lamentável), áreas quentes e as alavancas sugeridas. Reforce que é apoio à decisão, não veredito.

## Pesos do score (transparentes)

Engajamento 35 · Comp 25 · Estagnação 20 · Janela de churn 12 · Gestor com saídas 8. Bandas: Baixo 0-25, Médio 26-50, Alto 51-75, Crítico 76-100.

## Privacidade & ética

Dado individual sensível. Processamento 100% local: o roster nunca sai da máquina. Output é apoio ao planejamento de retenção, não decisão sobre pessoas. Sempre pareie com conversa de gestor.

## Lead capture

`eam_client.py` (raiz da skill): `on_first_run()` 1x por máquina + `record_run()` por execução. Email opcional + telemetria opt-in. Nunca envia o roster.

## Resources

| File | Purpose |
|---|---|
| `scripts/flight_risk.py` | Scoring explicável + HTML |
| `eam_client.py` | Lead capture + telemetria (sync de `eam/shared/`) |
