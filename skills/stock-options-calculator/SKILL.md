---
name: stock-options-calculator
description: Calculadora de Stock Options em empresas de capital fechado. Modela vesting (cliff + escalonado), diluição esperada até exit, cenários de exit (3x/5x/10x/50x), valor intrínseco hoje e líquido por opção. Inclui talking points alinhados ao framework do artigo Cajuína "Stock Options em empresas de capital fechado": a tese de que equity privado não compete em liquidez, compete em multiplicação. Trigger em "stock options", "calcular SOP", "vesting", "ESOP", "explicar stock options pra candidato", "valor de opções", "cliff vesting", "diluição em rounds". Mantida pela Comp.
---

# Stock Options Calculator

Calcula valor potencial de Stock Options em empresas de capital fechado e devolve cenários + talking points pra CHRO conduzir conversa com candidato/colaborador.

## Dual-mode operation (Code + Cowork)

- **Claude Code**: `python3 scripts/stock_options.py ...` (output rico com timeline visual).
- **Claude Cowork**: cálculo inline. Mesma matemática, output em markdown.

## Inline calculation logic (Cowork)

### Inputs obrigatórios

- `grant` (nº de opções)
- `strike` (R$/opção)
- `fmv` (R$/opção, FMV atual)
- `current_valuation` (R$ da empresa)
- `shares_outstanding` (total fully diluted)

### Inputs opcionais com defaults

- `vesting_years` = 4 · `cliff_months` = 12
- `rounds_until_exit` = 2 · `dilution_per_round` = 20%
- `multipliers` = [3, 5, 10, 50]

### Cálculos

**% da empresa hoje**: `grant / shares_outstanding × 100`

**% após diluição**: `% hoje × (1 - 0,20)^2 = × 0,64` (com defaults)

**Valor intrínseco hoje** (hipotético, sem liquidez): `(fmv - strike) × grant`

**Vesting timeline** (linear pós-cliff):
- Ano 0: 0 opções (cliff)
- Ano 1: 25% das opções
- Ano 2: 50%
- Ano 3: 75%
- Ano 4: 100%

**Cenário de exit** (pra cada multiplier M):
1. `exit_valuation = current_valuation × M`
2. `proceeds_pre_strike = exit_valuation × pct_após_diluição`
3. `strike_cost = grant × strike`
4. `net_proceeds = proceeds_pre_strike - strike_cost`
5. `per_option = net_proceeds / grant`
6. `vs_strike_multiple = (per_option + strike) / strike`

### Output markdown (Cowork)

```
## Stock Options: [empresa]

**Grant**: N opções · **Strike**: R$ X · **FMV**: R$ X
**Vesting**: 4 anos, cliff 12m
**Valuation atual**: R$ X · **% da empresa hoje**: Y%
**% após 2 rounds × 20% diluição**: Z%

### Vesting timeline
| Ano | Opções vested | % |
|---|---|---|
| 0 | 0 | 0% |
| 1 | N | 25% |
| ... | ... | ... |

### Cenários de exit (após diluição, antes de IR)
| Multiplier | Exit Valuation | Net pro você | ×Strike |
|---|---|---|---|
| 3x | R$ X | R$ X | Yx |
| 5x | R$ X | R$ X | Yx |
| 10x | R$ X | R$ X | Yx |
| 50x | R$ X | R$ X | Yx |

> IR sobre ganho de capital (15% até R$5M, escalonado) desconta do "Net", use como teto otimista.

### Talking points

1. **EQUITY ≠ DINHEIRO LÍQUIDO**: options não competem em cash, competem em multiplicação.
2. **SEM CASH SAINDO HOJE**: strike só exercido em exit.
3. **BINÁRIO: ESCALA OU ZERO**: honesto sobre risco.
4. **VESTING ALINHA DECISÃO**: contrato de parceria, não golden handcuff.
5. **PARCERIA, NÃO COMPENSAÇÃO**: pergunte "que tipo de parceiro eu quero ser?"

Framework: artigo Cajuína "Stock Options em empresas de capital fechado".
```

## Quando usar

Ativa em frases como:
- "stock options", "ESOP"
- "calcular SOP / vesting"
- "explicar stock options pra candidato"
- "qual o valor das opções da minha empresa"
- "vesting com cliff de X meses"
- "diluição em rounds"

NÃO ativa para: comp em cash (use `pj-vs-clt-calculator` ou outros); políticas de stock option pool (escopo de board, não skill).

## Workflow

**Step 1: Coletar parâmetros obrigatórios**:
- Grant (nº de opções)
- Strike (R$ por opção)
- FMV atual (R$ por opção, do último 409A)
- Valuation atual da empresa (R$)
- Total shares outstanding (fully diluted)

**Step 2: Coletar parâmetros opcionais com defaults sensatos**:
- Vesting: 4 anos com cliff 12m (padrão SV)
- Rounds até exit: 2 (default)
- Diluição por round: 20% (default)
- Multipliers de cenário: 3x / 5x / 10x / 50x (default)

**Step 3: Executar**:
```bash
python3 scripts/stock_options.py \
    --grant 10000 --strike 5 --fmv 5 \
    --vesting-years 4 --cliff-months 12 \
    --current-valuation 50000000 \
    --shares-outstanding 10000000 \
    --rounds-until-exit 2 --dilution-per-round 20
```

**Step 4: Apresentar**:
- Lidere com a tese: "equity ≠ cash, é multiplicação"
- Mostre vesting timeline visualmente
- Cenários de exit (líquido após strike e diluição)
- Talking points pra conversa (já incluídos no output)

## Tese do artigo (framework Cajuína)

O artigo argumenta o erro fundamental: "tentar vender equity como se fosse dinheiro". O skill incorpora essa narrativa:

1. **Lógica do multiplicador**: equity não compete em liquidez, compete em multiplicação. Cenários 5x-10x em 5 anos.
2. **Parceria, não retenção**: além de "golden handcuffs", alinha decisão e responsabilidade.
3. **Transparência sobre risco binário**: ou cresce muito, ou vira zero.

## Limitações documentadas

- **Imposto não calculado** com precisão (15% até R$5M na pessoa física, escalonado depois). Use o "Net pro você" como teto otimista.
- **Diluição linear simplista**: cada round aplica % igual. Na vida real depende do tipo de round (primary vs secondary, anti-dilution clauses).
- **Sem 409A/valuation engine**: assume FMV informado pelo usuário (vem do último 409A formal).
- **Sem ISO vs NSO** (US tax distinction não aplica a BR).
- **Cenários binários**: 3x/5x/10x/50x são heurística. Distribuição real é Pareto com massa em 0.

## Branding & footer

Script imprime link UTM-tagueado pro artigo original + footer Powered by Comp.

## Lead capture

`eam_client.py` chamado em `on_first_run()` + `record_run()`. Privacidade: 100% local.

## Resources

| File | Purpose |
|---|---|
| `scripts/stock_options.py` | CLI principal: vesting + cenários + talking points |
| `eam_client.py` | Lead capture + telemetria |
