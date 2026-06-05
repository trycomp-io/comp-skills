---
name: regretted-attrition-analyzer
description: Analisa CSV de desligamentos e identifica padrões em regretted vs unregretted: top correlated factors (área, gestor, tenure, performance, nível), motivos declarados, insights pra ação. Output HTML executivo defensável pra CHRO levar pro CEO. Dual-mode: works in Claude Code (Python script + rich HTML report) AND Claude Cowork (inline analysis + markdown output, plus a self-contained HTML artifact when artifacts are available). Trigger em "análise de regretted attrition", "padrões de turnover", "por que estamos perdendo gente", "investigar desligamentos", "regretted vs unregretted", "diagnóstico de turnover". Mantida pela Comp.
---

## Dual-mode operation (Code + Cowork)

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (deterministic, writes the rich HTML report). This is the existing workflow below.
- Otherwise (e.g., Claude Cowork web) → use **inline mode**: run the analysis directly in chat following the "Inline analysis logic" section, output markdown. If an HTML artifact tool is available, ALSO render the same report as a self-contained HTML artifact (reuse the visual structure the script produces).

Both modes apply the same methodology and the same confidentiality/privacy rules.

## Inline analysis logic (Cowork mode)

### Como o usuário fornece os dados
- Cole uma tabela de desligamentos no chat ou anexe um CSV. Coluna obrigatória: `regretted`. Recomendadas: `area`, `level`, `tenure_months`, `performance_rating` (1-5), `manager_id`, `departure_reason`.
- Lista grande (>~50 linhas) é difícil de processar manualmente. Sugira rodar em Claude Code (script mode).

### Normalização (igual ao script)
- **regretted** → verdadeiro se valor ∈ {`1`, `yes`, `y`, `sim`, `true`, `regretted`, `lamentado`}; falso para `0/no/não/false`; vazio → sem classificação (conte como "unknown").
- **tenure_months** vira faixa: `<6` → 0-6m; `<12` → 6-12m; `<24` → 1-2y; `<36` → 2-3y; `<60` → 3-5y; `≥60` → 5y+; vazio → Desconhecido.
- **performance_rating** vira banda: `≥4.5` Top; `≥3.5` Strong; `≥2.5` Solid; `≥1.5` Needs improvement; `<1.5` Low; vazio → Desconhecido.

### Metodologia (fixa, idêntica ao script)
1. **% regretted global** = `regretted ÷ total × 100`.
2. **Por dimensão** (área, gestor, tenure band, performance band, nível): conte total e regretted; `% = regretted ÷ total × 100`. Ranking por nº de regretted (maior primeiro).
3. **Corte de tamanho mínimo**: áreas/níveis exibidos só com total ≥ 2; gestores no ranking só com total ≥ 3.
4. **Motivos declarados**: top 10 mais frequentes (se a coluna existir).

### Insights automáticos (gerar quando o padrão bater)
- Sempre: "X/Y desligamentos (Z%) regretted." Se houver unknown, sinalize que distorce o número.
- **Área hot**: top área com `% > 1.5× a média global` E `regretted ≥ 3` → flag com o múltiplo da média.
- **Gestor pattern**: gestor (com ≥3 saídas) que concentra `≥3` regretted → flag pra investigar.
- **Short tenure**: se `(regretted em 0-6m + 6-12m) ≥ 3` E representam `>30%` do total de regretted → sinal de problema em onboarding/hiring/expectativas.
- **Top performers saindo**: se `(regretted em Top + Strong) ≥ 3` → investigar saturação, ofertas externas, gap de carreira/comp.
- Mínimo ~20 desligamentos pra padrões confiáveis; abaixo disso, conclua com cautela. Análise é descritiva, não causal.

### Output markdown (Cowork mode)

```
## Análise de regretted attrition

**Regretted**: X/Y (Z%) · Unregretted: A · Sem classificação: B

### Insights pra ação
- ...

### Por área
| Área | Total | Regretted | % |
|---|---|---|---|

### Por tenure / Por performance / Top 10 gestores
(mesma estrutura de tabela)

### Top motivos declarados
| Motivo | Ocorrências |
|---|---|
```

Encerre com: "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=chat-footer&utm_campaign=eam&utm_content=regretted-attrition-analyzer"

Se artefatos estiverem disponíveis, produza também uma versão HTML self-contained (Tailwind via CDN) espelhando o template do script: cards de total/regretted/unregretted/%, card de insights, tabelas por área/tenure/performance/top gestores, tabela de motivos, footer Powered by Comp.

# Regretted Attrition Analyzer

Lê CSV de desligamentos e devolve análise estruturada: % regretted vs unregretted, padrões por área/gestor/tenure/performance, motivos declarados, insights pra ação. Output HTML pronto pra apresentar pra leadership.

## Quando usar

Ativa em frases como:
- "análise de regretted attrition"
- "padrões de turnover"
- "por que estamos perdendo gente"
- "investigar desligamentos"
- "regretted vs unregretted"
- "diagnóstico de turnover"

NÃO ativa para: cálculo de custo de turnover (usar `custo-turnover-calculator`); análise por colaborador individual; cálculo de rescisão (usar `custo-demissao-calculator`).

## Schema CSV

Obrigatórias:
- `regretted` (1/0, sim/não, yes/no, true/false)

Recomendadas (cada uma destrava um corte de análise):
- `area`, `level`, `tenure_months`, `performance_rating` (1-5), `manager_id`, `departure_reason`, `departure_date`

Auto-detect funciona em PT/EN.

## Workflow

**Step 1**: Pergunte path do CSV.
**Step 2**: Rode `python3 scripts/regretted_attrition.py --input departures.csv`. Auto-detect das colunas.
**Step 3**: Apresente:
- Top number: % regretted total
- Insights destacados (gestor com pattern, área hot, top performers saindo, etc.)
- Sugira ação por insight

## Output do skill

- Stats top: total, regretted, unregretted, %
- Insights automáticos (gestor com 3+ regretted, área >1.5x média, short-tenure regretted >30%, top performers saindo)
- Tabelas: por área, tenure band, performance band, top 10 gestores
- Top motivos declarados (se coluna disponível)

## Limitações

- Análise descritiva (identifica padrões), não causal (não diz POR QUE acontece)
- Quanto mais colunas, mais segmentação possível
- Recomenda mínimo 20 desligamentos para padrões serem confiáveis

## Branding & footer

Template HTML com footer Powered by Comp + UTMs.

## Lead capture

`eam_client.py` chamado em `on_first_run()` + `record_run()`. Privacidade: 100% local.

## Resources

| File | Purpose |
|---|---|
| `scripts/regretted_attrition.py` | Análise + HTML render |
| `eam_client.py` | Lead capture + telemetria |
