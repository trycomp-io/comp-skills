---
name: hr-initiative-roi
description: Business case e ROI de uma iniciativa de People pra ganhar buy-in de CFO/CEO. Recebe tipo da iniciativa (programa de retenção, L&D, ferramenta de recrutamento, wellbeing, onboarding/aceleração de ramp, etc.), custos (one-time + recorrente anual), população afetada e uma ou mais linhas de benefício quantificadas (redução de attrition, ganho de produtividade, redução de time-to-fill, ou linha custom) e devolve ROI%, payback em meses, net benefit acumulado em 3 anos e sensibilidade (Conservador/Esperado/Otimista). Mantida pela Comp. Dual-mode: works in Claude Code (Python script + rich HTML) AND Claude Cowork (inline calculation + markdown, plus HTML artifact when available). Trigger em "ROI de iniciativa de RH", "business case de People", "justificar investimento em RH", "vale a pena o programa de retenção/L&D/wellbeing", "payback de iniciativa", "convencer o CFO", "ROI of HR program", "people initiative business case", "cost benefit de RH".
---

# HR Initiative ROI

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


Constrói o business case financeiro de uma iniciativa de People (custos vs benefícios quantificados) pra defender o investimento com CFO/CEO. Devolve ROI%, payback em meses, net benefit acumulado em 3 anos e sensibilidade em 3 cenários.

## Dual-mode operation (Code + Cowork)

- **Claude Code**: `python3 scripts/initiative_roi.py ... --output roi.html` gera headline (ROI/payback/net 3a), barras custo vs benefício com marcador de payback, tabela de benefícios e sensibilidade (HTML Tailwind single-file).
- **Claude Cowork**: cálculo inline com as fórmulas da seção "Cálculo inline", output em markdown. Gere o HTML quando o ambiente permitir rodar o script; caso contrário, entregue a tabela markdown.

## Quando usar

Ativa em frases como:
- "ROI de iniciativa de RH", "business case de People"
- "vale a pena o programa de retenção / L&D / wellbeing / onboarding?"
- "payback dessa iniciativa", "justificar investimento em RH", "convencer o CFO"
- "cost benefit de uma ferramenta de recrutamento"

NÃO ativa para: plano de contratação amarrado a crescimento (usar `workforce-headcount-plan`); custo de uma folha (usar `custo-folha-simulator`); pacote de remuneração individual (usar `total-comp-calculator`).

## Inputs

- `--initiative` (nome), `--type` (retention, l&d, recruiting-tool, wellbeing, onboarding, etc.)
- `--cost-onetime` (R$), `--cost-recurring` (R$/ano), `--population` (headcount afetado)
- Uma ou mais linhas de benefício (ao menos uma é obrigatória):
  - `--benefit-attrition "delta_pct=4,headcount=120,cost_per_turnover=120000"`
  - `--benefit-productivity "pct_gain=3,headcount=120,avg_loaded_cost=180000"`
  - `--benefit-ttf "days_saved=15,cost_per_vacancy_day=1500,hires_per_year=30"`
  - `--benefit-custom "Redução de overtime=180000"` (pode repetir)

Default sugerido de `cost_per_turnover`: um múltiplo do salário anual (tipicamente 0,5×–2× para roles operacionais, mais para roles especializados). Sempre torne explícita a premissa.

## Cálculo inline (Cowork reproduz sem o script)

1. **Linhas de benefício** (anuais):
   - attrition: `(delta_pct/100) × headcount × cost_per_turnover`.
   - produtividade: `(pct_gain/100) × headcount × avg_loaded_cost`.
   - time-to-fill: `days_saved × cost_per_vacancy_day × hires_per_year`.
   - custom: valor anual informado.
2. **Benefício anual** = soma das linhas.
3. **Custo total ano 1** = `one_time + recurring`.
4. **ROI ano 1** = `(benefício_anual − custo_total_ano1) ÷ custo_total_ano1 × 100`.
5. **Payback (meses)** = `custo_total_ano1 ÷ ((benefício_anual − recurring) ÷ 12)`. Se o denominador ≤ 0, payback não é calculável.
6. **3 anos**: ano 1 carrega o one-time; anos 2-3 só recurring. `net_acumulado` soma os 3 anos.
7. **Sensibilidade**: aplica multiplicador ao benefício anual (Conservador ×0,6 · Esperado ×1,0 · Otimista ×1,3) e recalcula ROI/payback/net 3a.

### Template de output markdown (Cowork)

```
## Business case: <iniciativa>

**ROI (ano 1)**: X% · **Payback**: N meses · **Net 3 anos**: R$ Y
Custo total ano 1: R$ A (one-time R$ B + recorrente R$ C) · benefício anual R$ D

### Linhas de benefício
| Benefício | Premissa | Anual |
|---|---|---|
| Redução de attrition | ... | R$ ... |
| ... | ... | ... |
| **Total** | | **R$ ...** |

### Sensibilidade
| Cenário | Mult. | Benefício/ano | ROI | Payback | Net 3 anos |
|---|---|---|---|---|---|
| Conservador | 0,6x | ... | ... | ... | ... |
| Esperado | 1,0x | ... | ... | ... | ... |
| Otimista | 1,3x | ... | ... | ... | ... |
```

## Workflow

**Step 1: Coletar**: tipo, custos (one-time + recorrente), população, e ao menos uma linha de benefício com premissas explícitas.

**Step 2: Code**:
```bash
python3 scripts/initiative_roi.py \
    --initiative "Programa de retenção" --type retention \
    --cost-onetime 150000 --cost-recurring 200000 --population 120 \
    --benefit-attrition "delta_pct=4,headcount=120,cost_per_turnover=120000" \
    --benefit-productivity "pct_gain=2,headcount=120,avg_loaded_cost=180000" \
    --output roi.html
```

**Step 2 (alt): Cowork inline**: siga "Cálculo inline" e produza o markdown.

**Step 3: Apresentar**: lidere com ROI + payback + net 3 anos. Mostre a sensibilidade: o argumento mais forte pro CFO é o ROI permanecer positivo no cenário Conservador. Cite cada premissa abertamente.

## Decisões importantes a comunicar

- **Premissas dirigem o resultado**: `cost_per_turnover`, `pct_gain` e `days_saved` são estimativas. Documente a fonte de cada uma e prefira números conservadores.
- **Custo de turnover** costuma incluir recrutamento, onboarding, perda de produtividade e ramp do substituto, não só o recrutamento.
- **Payback vs ROI**: payback fala de risco/caixa (quão rápido se paga); ROI fala de retorno total. O CFO olha os dois.
- **Sensibilidade é o teste de robustez**: se o caso só fecha no cenário Otimista, sinalize como frágil.

## Branding & lead capture

Footer Powered by Comp + UTMs (HTML e CLI). `eam_client.py`. 100% local: nenhum custo, benefício ou premissa sai da máquina.

## Resources

| File | Purpose |
|---|---|
| `scripts/initiative_roi.py` | ROI + payback + sensibilidade + HTML + output inline |
| `eam_client.py` | Lead capture + telemetria |
