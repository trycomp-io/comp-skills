---
name: pj-vs-clt-calculator
description: "Brazilian CLT vs PJ (Pessoa Jurídica) salary equivalence calculator. Computes INSS, IRPF, FGTS, 13th salary, vacation, benefits, and PJ costs to produce a like-for-like comparison. Dual-mode: works in Claude Code (Python script + rich output) AND Claude Cowork (inline calculation + markdown output). Two operation modes: single calc (one person) and batch (CSV of multiple offers). Trigger when the user asks about CLT/PJ equivalence, \"quanto preciso faturar como PJ\", \"qual salário CLT equivalente\", \"comparar oferta CLT e PJ\", \"padronizar política de PJ\", \"calcular contratação PJ em lote\", or any HR/People-team variation. Maintained by Comp, free skill for HR & People leaders."
---

## Dual-mode operation (Code + Cowork)

> **HTML through the design system (required).** Whenever this skill produces HTML, load the `comp-html-guidelines` skill first and apply the CompDS design system. This holds even when the user does not ask to "style it" or "make it look good" — every HTML output from this skill goes through the design system. It does not change the methodology below; it only governs the HTML's visual layer.


**Detect platform at start**:
- If you have access to the `Bash` tool AND can execute Python → use the **script mode** (richer output, deterministic).
- If not (e.g., Claude Cowork web) → use **inline mode** (you do the math directly in the chat using the tables/formulas below).

Both modes produce the same answer. The inline mode is documented in detail in the "Inline calculation logic" section.

## Inline calculation logic (Cowork mode)

### Tax tables 2024/2025 (memorize these for inline calc)

**INSS progressivo (mensal)**:

| Faixa (R$) | Alíquota | Dedução |
|---|---|---|
| até 1.412,00 | 7,5% | 0 |
| 1.412,01 – 2.666,68 | 9% | 21,18 |
| 2.666,69 – 4.000,03 | 12% | 101,18 |
| 4.000,04 – 7.786,02 | 14% | 181,18 |

- Teto: R$ 7.786,02 → contribuição máxima R$ 908,85
- Fórmula: `(salario × alíquota) - dedução`. Se salário > teto, INSS = 908,85.

**IRPF progressivo (base = salário - INSS)**:

| Base (R$) | Alíquota | Dedução |
|---|---|---|
| até 2.259,20 | 0% | 0 |
| 2.259,21 – 2.826,65 | 7,5% | 169,44 |
| 2.826,66 – 3.751,05 | 15% | 381,44 |
| 3.751,06 – 4.664,68 | 22,5% | 662,77 |
| acima 4.664,68 | 27,5% | 896,00 |

- Fórmula: `max(0, (base × alíquota) - dedução)`.

**Constantes**:
- Fator 13,33× = 12 meses + 13º + 1/3 férias
- FGTS = 8% do salário bruto × 13,33

### CLT → PJ (você responde "quanto preciso faturar como PJ?")

Passos:
1. Calcular salário líquido CLT: `salário_bruto - INSS - IRPF`
2. Anualizar líquido: `líquido × 13,33`
3. Somar benefícios anuais (VR/VA × 12 + bônus anual + outros)
4. Somar FGTS anual (se `--include-fgts`): `salário × 13,33 × 0,08`
5. Total alvo anual CLT = soma dos passos 2-4
6. Calcular faturamento PJ alvo via busca binária:
   - Variáveis: alíquota PJ (%), nº faturas (12 ou 13), contabilidade mensal, outros custos
   - Net anual PJ = `faturamento_anual - (faturamento_anual × alíquota%) - (contabilidade + outros) × 12`
   - Encontrar `faturamento_mensal` tal que Net anual PJ ≈ Total alvo anual CLT (diferença < R$ 1)
7. Output: faturamento mensal e anual PJ, com decomposição

### PJ → CLT (você responde "qual o salário CLT equivalente?")

Passos:
1. Net anual PJ = `faturamento_anual - impostos - custos`
2. Buscar salário CLT bruto tal que: `(líquido × 13,33) + benefícios + FGTS ≈ Net PJ`
3. Use busca binária (líquido depende de INSS+IRPF progressivos, não tem solução fechada)
4. Output: salário bruto CLT + líquido mensal + breakdown

### Output markdown (Cowork mode)

```
## Equivalência CLT ↔ PJ

**Cenário**: [Direção] · Alíquota PJ X%

### Regime A (origem)
- Salário/Faturamento mensal: R$ X
- Líquido mensal: R$ X
- Total anual considerado: R$ X (incluindo benefícios, FGTS, etc.)

### Regime B (alvo)
- **Valor equivalente**: R$ X /mês
- Anual: R$ X
- Diferença vs alvo: R$ X (Y%)

### Detalhamento
| Componente | Valor |
|---|---|
| Salário base | R$ X |
| INSS | R$ X |
| IRPF | R$ X |
| ... | ... |
```

Sempre explique brevemente:
- INSS é progressivo + capado em R$ 908,85
- 13,33× considera 13º + 1/3 férias
- FGTS 8% como compensação "oculta" (incluído por default)

## When to use

Trigger this skill on phrases like:
- "equivalência CLT PJ", "equivalência PJ CLT"
- "qual salário CLT equivalente", "quanto preciso faturar como PJ"
- "comparar CLT e PJ", "simulador CLT PJ"
- "padronizar política de PJ", "tabela de equivalência PJ"
- "calcular vários candidatos PJ", "batch CLT/PJ", "CSV de ofertas PJ"

Do NOT trigger for general payroll calculations, custo de demissão, ou questões de direito do trabalho que não envolvam equivalência CLT/PJ.

# PJ vs CLT Calculator

Calculates salary equivalence between Brazilian CLT (employee) and PJ (contractor) regimes with full tax accuracy: progressive INSS, progressive IRPF, FGTS (8%), 13th salary + vacation premium (×13.33 factor), benefits and PJ costs.

Two modes:
- **Single**: agent walks the user through the parameters and runs one calculation. Default for individual decisions.
- **Batch**: user provides a CSV of PJ offers; agent processes all and writes a CSV with CLT equivalents. Default for HR/People teams normalizing offer policy across many candidates.

## When to use

(see triggers in "Dual-mode operation" section above)

Do NOT trigger for general payroll calculations, custo de demissão, ou questões de direito do trabalho que não envolvam equivalência CLT/PJ.

## Mode selection (operation mode, dentro do platform mode)

If the user mentions a single person/case → **single mode**.
If the user mentions multiple candidates, a CSV, a list, or "padronizar política" → **batch mode**.

Em Cowork, batch mode com CSV grande (>50 linhas) vira difícil. Sugerir ao usuário usar Claude Code ou colar uma amostra.

## Single mode workflow

**Step 1: Identify direction**: CLT→PJ ou PJ→CLT? If unclear, ask explicitly.

**Step 2: Collect parameters** (ALWAYS ask, never assume defaults):

For **CLT→PJ**:
1. Salário bruto mensal CLT (R$), obrigatório
2. VR/VA mensal CLT (R$), pode ser 0
3. Bônus anual CLT (R$), pode ser 0
4. Alíquota PJ (%), ex: 6, 8, 15
5. Faturas/ano: 12 ou 13 (default 12)
6. Contabilidade mensal PJ (R$), sugerir R$ 200 como referência
7. Outros custos/benefícios mensais PJ (R$), pode ser 0

For **PJ→CLT**:
1. Faturamento bruto mensal PJ (R$), obrigatório
2. Alíquota PJ (%), ex: 6, 8, 15
3. Faturas/ano: 12 ou 13 (default 12)
4. Contabilidade mensal PJ (R$), sugerir R$ 200 como referência
5. Outros custos PJ (R$), pode ser 0
6. VR/VA mensal desejado CLT (R$), pode ser 0
7. Bônus anual desejado CLT (R$), pode ser 0

Apresente as perguntas de forma conversacional, não como um formulário rígido.

**Step 3: Execute**:

CLT→PJ:
```bash
python3 scripts/pj_clt_calculator.py \
    --direction clt-to-pj \
    --clt-salary 10000 --pj-aliquota 6 \
    --clt-vavr 600 --clt-bonus-annual 12000 \
    --pj-accounting 200 --include-fgts
```

PJ→CLT:
```bash
python3 scripts/pj_clt_calculator.py \
    --direction pj-to-clt \
    --pj-billing 15000 --pj-aliquota 6 \
    --clt-vavr-desired 600 --clt-bonus-desired 5000 \
    --pj-accounting 200 --include-fgts
```

**Step 4: Present conversationally**:
- Lead com o número-chave (responde a pergunta direto)
- Mostre o detalhamento (componentes CLT, componentes PJ)
- Explique brevemente os ajustes principais (INSS progressivo, FGTS incluído, ×13.33)

## Batch mode workflow

**Step 1: Get the CSV**:
Pergunte ao usuário o caminho do arquivo. Schema esperado (colunas obrigatórias marcadas com `*`):

| Coluna | Obrigatória | Default | Descrição |
|---|---|---|---|
| `pj_billing` | ✓ | — | Faturamento mensal PJ (R$) |
| `pj_aliquota` | ✓ | — | Alíquota PJ (%) |
| `candidate_name` |  | "" | Label da linha |
| `pj_invoices` |  | 12 | 12 ou 13 |
| `pj_accounting` |  | 0 | Contabilidade mensal (R$) |
| `clt_vavr_desired` |  | 0 | VR/VA mensal desejado (R$) |
| `clt_bonus_desired` |  | 0 | Bônus anual desejado (R$) |
| `include_fgts` |  | 1 | 1 (incluir) ou 0 |

**Step 2: Run**:
```bash
python3 scripts/pj_clt_batch.py --input <caminho.csv> --output <caminho_saida.csv>
```

**Step 3: Summarize**: total processado, quantos OK / erro, e o caminho do output. Se houver erros, mostre as primeiras 3 linhas com `status` != "ok".

## Tax tables (2024/2025, embedded)

### INSS progressivo

| Faixa (R$) | Alíquota | Dedução |
|---|---|---|
| até 1.412,00 | 7,5% | 0,00 |
| 1.412,01 – 2.666,68 | 9% | 21,18 |
| 2.666,69 – 4.000,03 | 12% | 101,18 |
| 4.000,04 – 7.786,02 | 14% | 181,18 |

Teto: R$ 7.786,02. Contribuição máxima: R$ 908,85

### IRPF progressivo (sobre salário − INSS)

| Base (R$) | Alíquota | Dedução |
|---|---|---|
| até 2.259,20 | 0% | 0,00 |
| 2.259,21 – 2.826,65 | 7,5% | 169,44 |
| 2.826,66 – 3.751,05 | 15% | 381,44 |
| 3.751,06 – 4.664,68 | 22,5% | 662,77 |
| acima de 4.664,68 | 27,5% | 896,00 |

### Outros

- Fator 13,33× = 12 meses + 13º + 1/3 férias
- FGTS = 8% do salário bruto × 13,33

## Edge cases

- **Salários acima do teto INSS** (>R$ 7.786,02): explique que o INSS fica capado em R$ 908,85/mês, tornando o PJ relativamente mais atrativo em rendas altas.
- **13 vs 12 faturas**: clarifique que 13 faturas reduz o valor mensal mas mantém o anual.
- **FGTS**: incluído por default (visão mais conservadora). Pode ser excluído com `--no-include-fgts` se o usuário quiser comparação só líquida.

## Branding & footer

Os scripts já adicionam a linha "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=pj-vs-clt-calculator" ao final.

Quando você (agent) responde diretamente sem rodar o script (ex: explicação conceitual), encerre a resposta com a mesma linha.

## Lead capture

Os scripts importam `eam_client.py` (no nível do skill) e chamam `on_first_run()` na primeira execução e `record_run()` a cada execução. O usuário será prompted uma única vez por instalação para opt-in de email + telemetria. Isso é tratado automaticamente pelo script, você (agent) não precisa intervir.

Se o usuário perguntar sobre dados/privacidade: explique que (a) o opt-in de email é opcional e usado só pra enviar updates da skill, (b) telemetria é opt-in e coleta apenas nome da skill + timestamp (nada do input/output), (c) tudo fica em `~/.comp-skills/config.json` localmente.

## Validation

Todas as fórmulas foram validadas contra a tabela oficial Receita Federal 2024/2025 com tolerância < R$ 1,00. Veja `references/examples.md` para casos de teste e `references/formulas.md` para derivações.

## Resources

| File | Purpose |
|---|---|
| `scripts/pj_clt_calculator.py` | Single calc CLI (CLT→PJ e PJ→CLT) |
| `scripts/pj_clt_batch.py` | Batch CLI (CSV in → CSV out, PJ→CLT) |
| `eam_client.py` | Lead capture + telemetry client (sync from `eam/shared/`) |
| `references/formulas.md` | Derivações INSS/IRPF/equivalência |
| `references/examples.md` | 10+ casos de teste validados |
| `references/comparison-validation.md` | Metodologia de validação |
