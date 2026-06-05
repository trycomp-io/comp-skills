---
name: reajuste-impact-calculator
description: "Calculadora de impacto financeiro de reajuste salarial (dissídio, mérito, ajuste pontual). Lê CSV/XLSX de roster + regra de reajuste (flat %, por nível ou por área) e devolve aumento total mensal/anual com encargos (~55.5%), % impacto na folha, breakdown por grupo. Trigger em \"impacto de reajuste\", \"custo de dissídio\", \"simular mérito\", \"quanto custa aumento de X%\", \"impacto na folha\", \"ciclo de mérito\". Mantida pela Comp."
---

# Reajuste Impact Calculator

Calcula o impacto financeiro completo (incluindo encargos) de um reajuste salarial: dissídio, ciclo de mérito, ajustes pontuais. Diferencia regras por nível, área ou flat.

## Dual-mode operation (Code + Cowork)

- **Claude Code**: `python3 scripts/reajuste_impact.py ...` (CSV roster).
- **Claude Cowork**: cálculo inline com regras passadas conversacionalmente OU com CSV pequeno colado.

## Inline calculation logic (Cowork)

### Constante chave

**Full load factor**: 1,555 (encargos patronais ~35,8% + provisões ~19,7%)

> Reajuste de R$ 1 em salário custa R$ 1,555 pro empregador.

### Modo Flat

Todos os colaboradores ganham X%.
1. `delta_salário_total_mensal = folha_atual × (X/100)`
2. `delta_com_encargos_mensal = delta_salário × 1,555`
3. `delta_anual = delta_com_encargos_mensal × 12`
4. `% impacto na folha = X%` (em salário) ou `X% × 1,555` (em custo total)

### Modo Por nível (ou por área)

CHRO informa regra: `{"Junior": 8, "Pleno": 5, "Senior": 4, "Manager": 3}` (% por nível).

Pra cada colaborador:
1. `aumento_individual = salário × (regra[nível] / 100)`
2. Soma todos: `delta_salário_mensal_total`
3. Aplica encargos: `× 1,555`
4. Anualiza: `× 12`

### Output markdown (Cowork)

```
## Impacto de reajuste: [Flat X% | Por nível | Por área]

**Headcount**: N · **Folha atual**: R$ X

### Delta
- ∆ salários mensal: R$ X (Y%)
- ∆ com encargos (×1,555): R$ X /mês
- **∆ anual com encargos: R$ X**

### Por grupo
| Grupo | HC | % | ∆ mensal (com encargos) |
|---|---|---|---|
| Junior | N | 8% | R$ X |
| Senior | N | 4% | R$ X |
| ... | ... | ... | ... |
```

**Princípio crítico** pra defender ao CFO: sempre comunique anualizado com encargos. CHRO esquece o ×1,555, CFO não.

## Quando usar

Ativa em frases como:
- "impacto de reajuste"
- "custo de dissídio"
- "simular mérito"
- "quanto custa dar X% de aumento"
- "impacto na folha"
- "ciclo de mérito"
- "negociação sindical, quanto sai"

NÃO ativa para: equidade salarial (usar `paygap-analysis-generator`); custo total de folha (usar `custo-folha-simulator`); rescisão (usar `custo-demissao-calculator`).

## Workflow

**Step 1: Pegar o arquivo + regra**:
- Path do CSV/XLSX do roster
- Tipo de regra:
  - **Flat**: mesmo % pra todo mundo (ex: dissídio coletivo de 5%)
  - **Por nível**: diferenciado (ex: Junior 8% / Pleno 5% / Senior 4% / Manager 3%)
  - **Por área**: diferenciado (ex: Eng 5% / Sales 4% / Backoffice 3%)

**Step 2: Rodar**:

```bash
# Flat
python3 scripts/reajuste_impact.py --input roster.csv --flat 5

# Por nível
python3 scripts/reajuste_impact.py --input roster.csv \
    --rule-by level --rules '{"Junior":8,"Pleno":5,"Senior":4,"Manager":3}'

# Por área
python3 scripts/reajuste_impact.py --input roster.csv \
    --rule-by area --rules '{"Eng":5,"Sales":4,"Backoffice":3}'
```

**Step 3: Apresentar**:
- Lidere com ∆ anual com encargos (número que o CFO vai querer)
- Mostre breakdown por grupo
- Compare: ∆ só salário vs ∆ com encargos (CHRO esquece o 55.5%)

## O que está incluso no cálculo

- **∆ salários** = soma dos aumentos individuais
- **∆ com encargos** = ∆ salários × 1.555 (encargos patronais ~35.8% + provisões ~19.7%)
- **% impacto na folha** = ∆ ÷ folha bruta atual
- Breakdown por grupo: HC, %, ∆ mensal com load

## Decisões importantes a documentar pro CHRO

- **Encargos contam**. Reajuste de 5% em R$100k salário não custa R$5k/mês, custa R$7.77k/mês.
- **Anualizado pesa mais**. R$7.77k/mês = R$93k/ano. CFO pensa em ano fiscal.
- **Diferenciação tem efeito surpreendente**: Senior 4% (poucos colaboradores, salário alto) frequentemente domina o ∆ total.

## Branding & footer

Script imprime footer "Powered by Comp" no fim.

## Lead capture

`eam_client.py` chamado em `on_first_run()` + `record_run()`. Privacidade: 100% local.

## Resources

| File | Purpose |
|---|---|
| `scripts/reajuste_impact.py` | CLI principal, flat ou diferenciado |
| `eam_client.py` | Lead capture + telemetria |
