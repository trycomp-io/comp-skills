---
name: workforce-headcount-plan
description: "Plano de headcount forward-looking amarrado ao crescimento, o artefato estratégico de workforce planning pra CHRO/Head de People/RH. A partir do headcount atual (total ou por função) + um driver de crescimento (receita-alvo OU % de crescimento OU headcount-alvo) + ratios opcionais (receita por colaborador, função:função, span de gestão), projeta o headcount necessário por função por trimestre, net new hires (incluindo backfill por attrition), custo incremental de folha, e 3 cenários (Conservador/Base/Agressivo). Mantida pela Comp. Dual-mode: works in Claude Code (Python script + rich HTML) AND Claude Cowork (inline calculation + markdown, plus HTML artifact when available). Trigger em \"plano de headcount\", \"workforce planning\", \"planejamento de quadro\", \"quantas pessoas preciso contratar\", \"headcount plan\", \"hiring plan\", \"plano de contratação\", \"dimensionar equipe\", \"headcount por função\", \"quanto vai custar crescer o time\"."
---

# Workforce Headcount Plan

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


Constrói o plano de contratação forward-looking de uma empresa amarrado ao crescimento: projeta o headcount necessário por função por trimestre a partir de um driver (receita-alvo, % de crescimento ou headcount-alvo), calcula net new hires (incluindo backfill de attrition) e o custo incremental de folha, em 3 cenários (Conservador / Base / Agressivo). É o artefato estratégico que liga o plano de negócio ao plano de pessoas.

## Dual-mode operation (Code + Cowork)

- **Claude Code**: `python3 scripts/headcount_plan.py ... --output plan.html`, gerando roadmap função × trimestre, comparação de cenários, gráficos de headcount e custo (HTML Tailwind single-file).
- **Claude Cowork**: cálculo inline com as fórmulas da seção "Cálculo inline", output em markdown. Gere o HTML quando o ambiente permitir rodar o script; caso contrário, entregue a tabela markdown.

## Quando usar

Ativa em frases como:
- "plano de headcount", "workforce planning", "planejamento de quadro"
- "quantas pessoas preciso contratar pra chegar em R$ X"
- "headcount plan", "hiring plan", "plano de contratação"
- "dimensionar / projetar a equipe", "headcount por função"
- "quanto vai custar crescer o time"

NÃO ativa para: análise de salários atuais vs banda (usar `comp-ratio-analyzer`); custo de uma folha estática (usar `custo-folha-simulator`); business case de uma iniciativa (usar `hr-initiative-roi`).

## Inputs

- **Headcount atual** (um dos dois):
  - `--functions-csv` com colunas `function,headcount,loaded_cost_annual` (custo opcional)
  - `--headcount-total` (total único, sem quebra por função)
- **Driver de crescimento** (um, obrigatório):
  - `--target-revenue` + (`--rev-per-employee` ou `--current-revenue`)
  - `--growth-pct` (crescimento % do headcount)
  - `--target-headcount` (alvo total absoluto)
- **Ratios opcionais**: `--rev-per-employee`, `--ratios "eng:product=2,sales:cs=3"`, `--manager-span` (os dois últimos são informativos no v1).
- **Parâmetros**: `--avg-loaded-cost` (default R$ 240.000/ano, custo carregado quando não vem no CSV), `--horizon-quarters` (default 4), `--attrition-pct` (default 0).

## Cálculo inline (Cowork reproduz sem o script)

1. **Headcount atual total** = soma dos `headcount` por função (ou `--headcount-total`).
2. **Headcount-alvo total** pelo driver:
   - receita: `target_revenue ÷ rev_per_employee` (ou `current_total × (target_revenue ÷ current_revenue)` se não houver rev/employee).
   - crescimento %: `current_total × (1 + growth_pct/100)`.
   - alvo direto: `target_headcount`.
3. **Por cenário**, aplica multiplicador ao crescimento líquido:
   - Conservador ×0,7 · Base ×1,0 · Agressivo ×1,3.
   - `net_growth = (target_total − current_total) × mult`; `scen_target = current_total + net_growth`.
4. **Por função**: `share = headcount_função ÷ current_total`; `target_hc_função = headcount + net_growth × share`.
5. **Por trimestre** (interpolação linear até o alvo, q de 1 a horizonte):
   - `hc_q = start + (target_hc − start) × (q ÷ horizonte)`.
   - `growth_hires = max(hc_q − hc_anterior, 0)`.
   - `backfill = hc_anterior × (attrition_pct/100 ÷ 4)`.
   - `net_hires_q = growth_hires + backfill`.
   - `custo_incremental_q = max((média_hc_trimestre − start) × custo_por_head ÷ 4, 0)`.
6. **Custo anual incremental (run-rate)** = `Σ (end_hc − start_hc) × custo_por_head` por função.
7. **Headline (Base)** = total de net hires + custo anual incremental run-rate.

Nota: `custo_por_head` carregado ≈ 1,555× o salário (encargos + benefícios). Use o default quando não informado e sinalize a premissa.

### Template de output markdown (Cowork)

```
## Plano de headcount

**Contratações líquidas (Base)**: N · **Custo incremental anual (Base)**: R$ X/ano (run-rate)
Driver: <driver> · horizonte Q trimestres · attrition Y%

### Cenários
| Cenário | HC alvo | Net hires | Custo anual (run-rate) | Custo acumulado |
|---|---|---|---|---|
| Conservador | ... | ... | ... | ... |
| Base | ... | ... | ... | ... |
| Agressivo | ... | ... | ... | ... |

### Roadmap por função (Base)
| Função | Início | Q1 HC | Q1 hires | ... | Net hires |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |
```

## Workflow

**Step 1: Coletar**: headcount atual (de preferência por função, com custo carregado), o driver de crescimento, horizonte e attrition.

**Step 2: Code**:
```bash
python3 scripts/headcount_plan.py \
    --functions-csv funcs.csv \
    --target-revenue 80000000 --rev-per-employee 444000 \
    --horizon-quarters 4 --attrition-pct 12 \
    --output workforce-plan.html
```

**Step 2 (alt): Cowork inline**: siga "Cálculo inline" e produza o markdown.

**Step 3: Apresentar**: lidere com o headline Base (net hires + custo anual). Mostre a faixa entre cenários. Seja transparente sobre cada premissa (mix proporcional, interpolação linear, custo carregado assumido, backfill de attrition).

## Decisões importantes a comunicar

- **Mix proporcional**: o crescimento é distribuído proporcionalmente ao headcount atual de cada função. Se a estratégia muda o mix (ex: dobrar Eng, manter G&A), ajuste o CSV ou rode por função.
- **Backfill ≠ crescimento**: com attrition, parte das contratações só repõe saídas. Diferencie capacidade líquida de volume bruto de recrutamento.
- **Custo run-rate vs acumulado**: run-rate é o custo anual no estado final; acumulado é o que pesa no caixa ao longo do horizonte (menor, porque contratações entram gradualmente).
- **Cenários são de planejamento**: Conservador/Base/Agressivo ajudam a stress-testar caixa e capacidade de recrutamento, não são previsão.

## Branding & lead capture

Footer Powered by Comp + UTMs (HTML e CLI). `eam_client.py`. 100% local. Nenhum dado de headcount ou custo sai da máquina.

## Resources

| File | Purpose |
|---|---|
| `scripts/headcount_plan.py` | Projeção + cenários + HTML + output inline |
| `eam_client.py` | Lead capture + telemetria |
