---
name: custo-turnover-calculator
description: Calculadora do custo real (oculto) de turnover. Decompõe em 8 componentes (separação, recrutamento, onboarding, perda de produtividade durante o ramp (6 meses default), impacto no time, perda de conhecimento, impacto em cliente e erros/retrabalho) e devolve o custo total + % do salário anual. Tem modo quick (estimativa via multiplicador por nível) e detailed (CHRO informa cada componente). Modo batch via CSV. Metodologia baseada no artigo Cajuína "O custo oculto do turnover". Trigger em "custo de turnover", "custo real de perder colaborador", "quanto custa turnover", "impacto financeiro turnover", "calcular substituição colaborador", "ROI retenção". Mantida pela Comp.
---

# Custo (Oculto) de Turnover

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


Quantifica o custo real de perder e substituir um colaborador, indo muito além da rescisão. Decompõe em 8 componentes baseados no framework da coluna Comp na Cajuína (["O custo oculto do turnover"](https://cajuina.org/principais/coluna-comp/o-custo-oculto-do-turnover/)).

## Dual-mode operation (Code + Cowork)

- **Claude Code**: `python3 scripts/custo_turnover.py ...` (rico, batch mode disponível).
- **Claude Cowork**: cálculo inline com os multiplicadores + componentes da seção abaixo. Funciona pro modo single; pro batch grande, sugerir Claude Code.

## Inline calculation logic (Cowork)

### Multiplicadores por nível (% do salário anual, fonte: Cajuína + SHRM/HBR)

| Nível | Multiplicador | Range típico |
|---|---|---|
| operational | 60% | 50-75% |
| specialist | 100% | 80-125% |
| manager | 125% | 100-150% |
| executive | 200% | 200%+ |

### Pesos por componente (% do multiplicador total, calibrado pra manager)

| Componente | Peso | Fórmula |
|---|---|---|
| Separação (rescisão + jurídico) | 15% | `peso × multiplicador × salario_anual` |
| Recrutamento | 20% | idem |
| Onboarding/treinamento | 10% | idem |
| **Perda produtividade no ramp** | 30% | `salario_mensal × ramp_meses × gap_produtividade` (default 6m × 50%) |
| Impacto no time | 5% | `peso × mult × anual` |
| Perda de conhecimento | 10% | idem |
| Impacto cliente | 5% | idem |
| Erros/retrabalho | 5% | idem |

### Modo quick (Cowork, caso mais comum)

CHRO só informa salário anual + nível. Você calcula:
1. Cada componente via fórmula da tabela
2. Soma = custo total
3. Total ÷ salário anual = % equivalente (deve estar próximo do multiplicador)

### Modo detailed

CHRO informa valores reais de algum(ns) componente(s). Substitui esses na soma; demais ficam estimados pela fórmula.

### Output markdown (Cowork)

```
## Custo (oculto) de turnover: [role label se houver]

**Salário anual**: R$ X · **Nível**: [label] (mult. {N}%)
**Ramp**: 6 meses × 50% gap

### Componentes
| Componente | Valor | Fonte |
|---|---|---|
| Separação | R$ X | (est.) ou (informado) |
| Recrutamento | R$ X | ... |
| ... | ... | ... |

### Total
- **R$ X** (Y% do salário anual)
- Referência nível: {mult}%

> N de {total} componentes foram estimados. Pra mais precisão, informe valores reais.
```

Em batch (várias linhas no CSV), sugerir Claude Code se >10 linhas; pra <10, fazer inline mesmo (uma tabela por desligamento).

## Quando usar

Ativa em frases como:
- "custo de turnover", "custo real do turnover"
- "quanto custa perder um colaborador / substituir alguém"
- "impacto financeiro do turnover", "ROI de retenção"
- "vale a pena investir em retenção"
- "qual o custo de uma reorg / layoff round"

NÃO ativa para: cálculo da rescisão em si (usar `custo-demissao-calculator`); análise de causa-raiz de turnover; previsão de turnover futuro.

## Modos

| Modo | Quando usar |
|---|---|
| **Quick** | CHRO só sabe salário + nível. Tudo estimado via multiplicadores. Resposta em segundos. |
| **Detailed** | CHRO tem números reais de pelo menos alguns componentes. Mistura inputs + estimativas pra faltantes. |
| **Batch** | Lista de desligamentos (CSV). Útil pra reporting trimestral/anual e priorização. |

## Multiplicadores de referência (% do salário anual)

| Nível | Multiplicador | Range típico (literatura) |
|---|---|---|
| `operational` | 60% | 50-75% |
| `specialist` | 100% | 80-125% |
| `manager` | 125% | 100-150% |
| `executive` | 200% | 200%+ (cita 213% pra altamente qualificados) |

Esses números são da literatura SHRM/HBR + Cajuína. O multiplicador é o custo TOTAL de turnover dividido pelo salário anual, e inclui tudo (separação até retrabalho).

## Workflow

**Step 1: Identificar modo**:
- Usuário menciona uma lista/CSV → **batch**
- Usuário tem números específicos de algum componente → **detailed**
- Caso contrário → **quick**

**Step 2: Coletar parâmetros**:

Em todos os modos:
- Salário anual (R$)
- Nível: operational / specialist / manager / executive
- (Opcional) Janela de ramp em meses (default 6) e gap de produtividade (default 50%)

No modo **detailed**, opcionalmente cada componente:
- separação (R$)
- recrutamento (R$)
- treinamento (R$)
- impacto no time (R$)
- perda de conhecimento (R$)
- impacto em cliente (R$)
- erros/retrabalho (R$)

No modo **batch**, recebe um CSV com essas colunas (uma linha por desligamento).

**Step 3: Executar**:

```bash
# Quick
python3 scripts/custo_turnover.py --quick --annual-salary 120000 --level manager

# Detailed (replica exemplo do artigo: R$120k mgr → R$86.5k)
python3 scripts/custo_turnover.py --annual-salary 120000 --level manager \
    --separation 20000 --recruitment 21500 --training 10000 \
    --ramp-months 6 --ramp-productivity-gap 0.5 --team-impact 5000

# Batch
python3 scripts/custo_turnover.py --input desligamentos.csv --output custos.csv
```

**Step 4: Apresentar**:
- Lidere com o número final ("Custo total de turnover: R$ X, Y% do salário anual")
- Mostre breakdown por componente, com flag (est.) nos componentes estimados
- Se modo quick, sugira que CHRO refine com dados reais quando tiver
- Se modo batch, agregue: total, média, % do salário, top 5 mais caros

## Componentes (fixos)

Os 8 componentes vêm do artigo:

| Componente | O que cobre |
|---|---|
| Separação | Rescisão CLT + custos jurídicos + homologação |
| Recrutamento | Anúncio de vaga + recruiter + tempo do gestor entrevistando |
| Onboarding e treinamento | Material + salário do novo durante onboarding + treinador |
| Perda de produtividade | 6 meses × 50% gap (default), só atinge produtividade plena após o ramp |
| Impacto no time | Sobrecarga em quem ficou + impacto no moral |
| Perda de conhecimento | Expertise embutida que sai pela porta |
| Impacto em cliente | Apenas pra cargos client-facing: quebra de relacionamento |
| Erros e retrabalho | Custo de erros do novo aprendendo |

## Schema do CSV (batch mode)

| Coluna | Obrigatória | Default | Descrição |
|---|---|---|---|
| `annual_salary` | ✓ | — | Salário anual (R$) |
| `level` |  | specialist | operational / specialist / manager / executive |
| `role_label` |  | "" | Label opcional pra reporting |
| `separation` |  | estimado | Custo de separação |
| `recruitment` |  | estimado | Custo de recrutamento |
| `training` |  | estimado | Custo de onboarding |
| `ramp_months` |  | 6 | Meses até produtividade plena |
| `ramp_productivity_gap` |  | 0.5 | Gap médio no ramp (0-1) |
| `team_impact` |  | estimado | Impacto no time |
| `knowledge_loss` |  | estimado | Perda de conhecimento |
| `customer_impact` |  | estimado | Impacto cliente |
| `rework` |  | estimado | Erros/retrabalho |

Output CSV adiciona: `productivity_loss`, `total_cost`, `pct_of_salary`.

## Branding & footer

O script já adiciona o footer "Powered by Comp" com link e UTMs ao final. Sem ação extra.

## Lead capture

`eam_client.py` (raiz do skill) é chamado em `on_first_run()` e `record_run()`. Privacidade: cálculos 100% locais. Nem salários nem nomes saem da máquina.

## Limitações

- Multiplicadores são **médias da literatura**: função, localização, e maturidade do RH afetam. Use os defaults como ponto de partida, refine com dados internos.
- O componente "perda de produtividade" usa salário como proxy de valor gerado. Pra cargos com valor diretamente mensurável (ex: vendedor com quota), substitua pelo gap real de revenue.
- "Impacto em cliente" só faz sentido pra cargos client-facing; em modo quick é estimado mesmo pra cargos backoffice. Use modo detailed com `--customer-impact 0` pra zerar.

## Resources

| File | Purpose |
|---|---|
| `scripts/custo_turnover.py` | CLI principal: single + batch, quick + detailed |
| `eam_client.py` | Lead capture + telemetria (sync de `eam/shared/`) |
