---
name: custo-demissao-calculator
description: Calculadora de custo de rescisão CLT brasileira. Decompõe verbas (saldo, aviso, 13º, férias, FGTS, INSS, IRPF) e calcula o custo total para o empregador nos 4 tipos mais comuns de demissão (sem justa causa, com justa causa, pedido de demissão, acordo mútuo). Dual-mode: funciona em Claude Code (script Python) e Claude Cowork (cálculo inline). Trigger em "custo de demissão", "rescisão CLT", "quanto custa demitir", "calcular rescisão", "verbas rescisórias", "homologação CLT", "rescisão por acordo", "art. 484-A", "multa FGTS rescisão". Mantida pela Comp.
---

# Custo de Demissão CLT

Calcula o custo total de uma rescisão trabalhista CLT no Brasil, com decomposição completa das verbas e dos encargos do empregador. Cobre os 4 tipos mais comuns de término de contrato.

## Dual-mode operation (Code + Cowork)

- **Claude Code**: tem Bash + Python → `python3 scripts/custo_demissao.py ...` produz output rico e determinístico.
- **Claude Cowork**: web app, sem Python → **cálculo inline** seguindo as fórmulas da seção "Inline calculation logic" abaixo.

Mesma resposta nas duas plataformas.

## Inline calculation logic (Cowork)

### Tabelas (INSS + IRPF 2024/2025)

São as mesmas do `pj-vs-clt-calculator`. INSS progressivo capado em R$ 908,85 (teto R$ 7.786,02). IRPF progressivo sobre base = salário - INSS.

### Constantes
- FGTS 8% do salário bruto, mensal.
- Multa FGTS rescisória: 40% (sem justa causa) ou 20% (acordo art. 484-A) sobre o saldo FGTS.
- Encargo empregador FGTS sobre verbas: 8% sobre o que é indenizado/proporcional.

### Aviso prévio (dias)
`30 + 3 × anos_completos_de_servico`, capado em **90 dias** (Lei 12.506/2011).

### Cálculo por tipo

**Sem justa causa** (empregador demite):
- Saldo de salário (`salario × dias_trabalhados_mes / dias_no_mes`)
- Aviso prévio indenizado OU trabalhado (se trabalhado, sem custo extra)
- 13º proporcional (`salario × meses_no_ano / 12`; mês conta se ≥15 dias trabalhados)
- Férias proporcionais + 1/3 (avos do período aquisitivo atual × 1,333)
- Férias vencidas + 1/3 (se houver) = 1 salário × 1,333
- **Multa FGTS 40%** sobre saldo
- INSS/IRPF descontam separado sobre saldo e sobre 13º

**Com justa causa**:
- Apenas saldo + férias vencidas + 1/3 (se houver). Sem aviso, 13º, férias proporcionais, multa.

**Pedido de demissão** (colaborador pede):
- Saldo + 13º proporcional + férias proporcionais + 1/3
- Aviso: se não cumpriu, **desconta** do colaborador
- Sem multa FGTS, sem saque

**Acordo (art. 484-A, Lei 13.467/2017)**:
- Saldo + 50% aviso indenizado + 13º proporcional + férias proporcionais + 1/3
- **Multa FGTS 20%** (metade da 40%)
- Saque 80% do FGTS (vs 100% sem justa causa)

### Custo total do empregador = soma verbas + multa FGTS + FGTS sobre verbas (~8% das indenizadas)

### Output markdown (Cowork)

```
## Rescisão CLT: [tipo]

**Salário base**: R$ X · **Admissão**: data · **Demissão**: data · **Tempo de empresa**: N anos

### Verbas devidas
| Verba | Valor |
|---|---|
| Saldo de salário | R$ X |
| Aviso prévio (N dias, indenizado) | R$ X |
| 13º proporcional (N/12 avos) | R$ X |
| Férias proporcionais + 1/3 | R$ X |
| (se houver) Férias vencidas + 1/3 | R$ X |
| **Subtotal bruto** | **R$ X** |

### Descontos
| Desconto | Valor |
|---|---|
| INSS sobre saldo | R$ X |
| IRPF sobre saldo | R$ X |
| INSS sobre 13º | R$ X |
| IRPF sobre 13º | R$ X |
| **Total descontos** | **R$ X** |

### Resumo
- **Líquido pro colaborador**: R$ X
- **Multa FGTS** (paga via GRRF): R$ X
- **Saque FGTS disponível**: R$ X

### Custo total empregador
**R$ X** (verbas + multa FGTS + FGTS sobre verbas ~8%)
```

Sempre cite as limitações ao apresentar:
- Tabelas IR/INSS 2024/2025 (atualizam em fevereiro)
- Não cobre estabilidades (gestante, dirigente sindical), contratos prazo determinado, dispensa discriminatória
- Honorários de homologação não inclusos

## Quando usar

Ativa em frases como:
- "custo de demissão", "rescisão CLT"
- "quanto custa demitir X"
- "calcular rescisão", "verbas rescisórias"
- "homologação CLT"
- "rescisão por acordo", "rescisão mútua", "art. 484-A"
- "multa FGTS na rescisão"

NÃO ativa para: cálculo de folha mensal normal (usar futura skill `custo-folha-simulator`); equivalência CLT vs PJ (usar `pj-vs-clt-calculator`); dúvidas conceituais de direito trabalhista (não é função do skill).

## Tipos suportados

| Tipo | O que cobre |
|---|---|
| `sem_justa_causa` | Empregador demite sem motivo. Aviso (trabalhado ou indenizado), 13º proporcional, férias proporcionais + 1/3, multa 40% FGTS, saque integral. |
| `com_justa_causa` | Empregador demite por falta grave. Apenas saldo + férias vencidas (se houver). Sem aviso, sem 13º proporcional, sem multa. |
| `pedido_demissao` | Colaborador pede para sair. 13º proporcional + férias proporcionais. Aviso pode ser descontado se não cumprido. Sem multa, sem saque. |
| `acordo` | Mútuo acordo (Lei 13.467/2017, art. 484-A). 50% aviso indenizado + 20% multa FGTS + 80% saque. |

Fora do escopo atual (V1): contratos por prazo determinado, gestante, dirigente sindical, indenização adicional por dispensa discriminatória.

## Workflow

**Step 1: Coletar parâmetros obrigatórios**:
1. Tipo de demissão (das 4 opções acima)
2. Salário bruto mensal (R$)
3. Data de admissão (YYYY-MM-DD)
4. Data de demissão (YYYY-MM-DD), default hoje se não informado

**Step 2: Coletar parâmetros opcionais relevantes**:

Para `sem_justa_causa` e `pedido_demissao`:
- Aviso prévio: `indenizado` (default), `trabalhado` ou `dispensado`

Para qualquer tipo:
- Férias vencidas (0 ou 1): tem período não-gozado a vencer?
- Saldo FGTS real (se o usuário souber); se não, estima 8% × meses × salário
- Benefícios extras mensais (VR/VA, etc.) que entram proporcional ao saldo

**Step 3: Executar**:

```bash
python3 scripts/custo_demissao.py \
    --tipo sem_justa_causa \
    --salario 10000 \
    --data-admissao 2022-01-15 \
    --data-demissao 2026-05-30 \
    --aviso indenizado
```

**Step 4: Apresentar**: lidere com o "Custo total para o empregador". Depois mostre o detalhamento por verba (devidas + descontos) e o resumo do colaborador (líquido + multa FGTS + saque disponível). Explique brevemente o que cada componente representa se o usuário pedir.

## Metodologia (fixa, baseada na CLT 2024/2025)

### Aviso prévio
- 30 dias base + 3 dias por ano completo de serviço
- Capado em 90 dias (Lei 12.506/2011)

### 13º proporcional
- 1/12 do salário por mês trabalhado no ano corrente
- Mês conta se ≥ 15 dias trabalhados

### Férias proporcionais
- 1/12 por mês trabalhado no período aquisitivo atual (último aniversário de admissão até demissão)
- Acrescido de 1/3 constitucional

### FGTS
- Saldo acumulado = 8% × salário × meses (estimativa quando não informado)
- Multa rescisória: 40% (sem justa causa) ou 20% (acordo) sobre o saldo
- Empregador deposita 8% sobre as verbas rescisórias indenizadas (FGTS sobre rescisão)

### INSS / IRPF
- Tabelas progressivas 2024/2025 da Receita Federal
- Aplicados separadamente sobre saldo e sobre 13º (cálculo distinto)
- Férias vencidas/proporcionais indenizadas: IRPF tem exceções não totalmente cobertas no V1 (verifique com seu contador para casos críticos)

## Edge cases & limitações

- **Salários acima do teto INSS** (R$ 7.786,02): INSS capa em R$ 908,85.
- **Estimativa FGTS**: sem o saldo real, a estimativa subestima/superestima se o salário variou ao longo do contrato. Sempre prefira o saldo extraído do app FGTS.
- **Justa causa**: a CLT não dá 13º proporcional nem férias proporcionais ao colaborador demitido por justa causa (entendimento majoritário do TST). Skill segue esse padrão.
- **Custo de seguro desemprego**: não calculado (é benefício do colaborador, não custo do empregador).
- **Honorários de homologação**: não incluídos.

## Branding & footer

O script já adiciona o footer "Powered by Comp" com link e UTMs ao final do output. Não precisa de ação extra do agente.

## Lead capture

`eam_client.py` (na raiz do skill) é chamado em `on_first_run()` no início e `record_run()` no fim. Prompt de opt-in (email + telemetria) aparece uma única vez por máquina.

Privacidade: cálculos são 100% locais. Dados de salário e datas nunca saem da máquina do usuário. Apenas nome do skill + timestamp na telemetria (se opt-in).

## Resources

| File | Purpose |
|---|---|
| `scripts/custo_demissao.py` | CLI principal: 4 tipos de rescisão + breakdown completo |
| `eam_client.py` | Lead capture + telemetria (sync de `eam/shared/`) |
