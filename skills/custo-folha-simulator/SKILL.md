---
name: custo-folha-simulator
description: Simulador de custo total de folha de pagamento (Brasil). Inclui encargos patronais (INSS 20%, FGTS 8%, SAT 2%, Sistema S 5.8%), provisões (13º, férias+1/3, multa FGTS rescisória) e benefícios. Dois modos: detalhado (CSV de roster) ou estimativa (headcount + salário médio). NÃO substitui sistema de folha real; é simulação rápida pra orçamento, projeção, cenários. Trigger em "custo de folha", "simulador de folha", "custo total empregador", "quanto custa folha de X colaboradores", "encargos sobre folha", "onerated factor". Mantida pela Comp.
---

# Custo de Folha Simulator

Simula o custo TOTAL empregador da folha brasileira em segundos. Não executa folha (use seu HRIS pra isso): serve pra orçamento, projeção, cenários.

## Dual-mode operation (Code + Cowork)

- **Claude Code**: `python3 scripts/custo_folha.py ...` (CSV de roster ou estimate).
- **Claude Cowork**: cálculo inline com as taxas abaixo. Modo estimate é nativo; modo CSV grande sugerir Code.

## Inline calculation logic (Cowork)

### Taxas (Brasil 2024/2025)

**Encargos patronais** (~35,8%):
- INSS patronal: 20%
- FGTS: 8%
- SAT: 2% (varia 1-3% por CNAE, default 2%)
- Sistema S + salário-educação + INCRA: 5,8%

**Provisões mensais** (~19,7%):
- 13º salário: 8,33% (1/12)
- Férias: 8,33% (1/12)
- 1/3 constitucional: 2,78%
- Multa FGTS rescisória provisionada: ~0,27%/mês

**Onerated factor**: ~1,555 (salário × 1,555 = custo total mensal, sem benefícios extras)

### Modo estimate (Cowork, caso comum)

CHRO informa: headcount + salário médio + (opcional) benefícios médios mensais.

Cálculo:
1. `total_salário = headcount × salário_médio`
2. `encargos = total_salário × 0,358`
3. `provisões = total_salário × 0,197`
4. `benefícios = headcount × (VR/VA + outros)`
5. `custo_mensal = total_salário + encargos + provisões + benefícios`
6. `custo_anual = custo_mensal × 12`

### Modo detailed (CSV)

Pra <50 linhas no Cowork: cole o CSV, calcula linha por linha somando. Pra ≥50: usar Code.

### Output markdown (Cowork)

```
## Custo de folha: modo ESTIMATE

**Headcount**: N · **Salário médio**: R$ X

| Componente | Valor mensal |
|---|---|
| Salários brutos | R$ X |
| Encargos patronais (~36%) | R$ X |
| Provisões (~20%) | R$ X |
| Benefícios (VR/VA + outros) | R$ X |
| **Custo mensal total** | **R$ X** |
| **Custo anual total** | **R$ X** |

**Onerated factor**: {factor}x salário

> Não substitui sistema de folha real. SAT varia por CNAE; Sistema S por setor. Pra precisão fiscal use sua folha.
```

## Quando usar

Ativa em frases como:
- "custo de folha", "simulador de folha"
- "custo total empregador", "onerated factor"
- "quanto custa folha de X colaboradores"
- "encargos sobre folha"
- "quanto sai a folha total no fim do mês"
- "projeção de custo de folha"

NÃO ativa para: rodar folha real (não substitui sistema); rescisão (usar `custo-demissao-calculator`); equivalência CLT/PJ (usar `pj-vs-clt-calculator`).

## Modos

| Modo | Quando usar |
|---|---|
| **Detailed** | Tem CSV/XLSX de roster com salários individuais. Mais preciso. |
| **Estimate** | Só sabe headcount + salário médio. Rápido pra planejamento. |

## Workflow

**Detailed**:
1. Pergunte path do CSV
2. Rode `python3 scripts/custo_folha.py --input roster.csv`
3. Auto-detect das colunas (salary obrigatória; opcionais: area, vr_va, outros)

**Estimate**:
1. Pergunte headcount + salário médio + (opcional) benefícios médios
2. Rode `python3 scripts/custo_folha.py --headcount 50 --salario-medio 8000 --vr-va-medio 800`

## Componentes do cálculo (fixos)

**Encargos patronais** (~35.8%):
- INSS patronal: 20%
- FGTS: 8%
- SAT (Seguro Acidente Trabalho): 2% (varia 1-3% por CNAE, default 2%)
- Sistema S + salário-educação + INCRA: ~5.8%

**Provisões** (~19.7%):
- 13º salário: 8.33% (1/12)
- Férias: 8.33% (1/12)
- 1/3 constitucional de férias: 2.78%
- Multa FGTS rescisória provisionada: ~0.27%/mês

**Benefícios**: adicionado ao custo total sem incidir encargos (VR/VA tem incidência reduzida via PAT).

**Onerated factor**: custo total mensal ÷ folha bruta. Tipicamente 1.55-1.75x.

## Limitações (V1, documentar pro CHRO)

- Não considera benefícios com incidência (plano saúde como salário in natura, ajuda de custo tributável, etc.); informe via `--outros-medio`
- Não diferencia mensalistas vs horistas
- Não calcula INSS/IRPF do colaborador (esse é desconto, não custo)
- SAT default 2% (verifique CNAE da empresa pra valor real)
- Sistema S simplificado (não diferencia por setor; comercial/industrial/transporte têm % diferentes)

Pra precisão fiscal use sua folha real. Aqui é simulação.

## Branding & footer

Script imprime footer "Powered by Comp" com link UTM-tagueado no fim do CLI.

## Lead capture

`eam_client.py` chamado em `on_first_run()` + `record_run()`. Privacidade: cálculos 100% locais.

## Resources

| File | Purpose |
|---|---|
| `scripts/custo_folha.py` | CLI: detailed (CSV) + estimate modes |
| `eam_client.py` | Lead capture + telemetria |
