---
name: total-comp-calculator
description: Calculadora de Total Compensation (modelo Comp). Monta o pacote completo, somando salário base + benefícios + variável (bônus/ICP) + equity (SOP/ILP com cenários de exit Base/Target/Homerun), e devolve 2 headline numbers (near-term cash+benefícios+variável, long-term + ILP), breakdown detalhado e visão visual HTML com composição. Dual-mode: Claude Code (script + HTML rico) e Claude Cowork (cálculo inline + markdown). Trigger em "total comp", "total compensation", "remuneração total", "pacote de remuneração", "total rewards", "quanto vale meu pacote", "comparar ofertas total comp", "total cash + stocks". Mantida pela Comp.
---

# Total Compensation Calculator

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


Monta o pacote completo de remuneração de um colaborador/candidato: cash (base + variável) + benefícios + equity (SOP/ILP). Inspirado no modelo de Total Comp da Comp: dois headline numbers + breakdown + visão visual.

## Dual-mode operation (Code + Cowork)

- **Claude Code**: `python3 scripts/total_comp.py ... --output tc.html` (HTML visual com composição + tabelas).
- **Claude Cowork**: cálculo inline com as fórmulas abaixo, output em markdown.

## Quando usar

Ativa em frases como:
- "total comp", "total compensation", "remuneração total"
- "pacote de remuneração", "total rewards"
- "quanto vale meu pacote / a oferta"
- "comparar ofertas em total comp"
- "total cash + stocks"

NÃO ativa para: só equivalência CLT/PJ (usar `pj-vs-clt-calculator`); só stock options (usar `stock-options-calculator`); custo empregador da folha (usar `custo-folha-simulator`).

## Modelo (estrutura fixa)

### Componentes

1. **Cash**:
   - Salário base mensal × **13,33** (12 + 13º + 1/3 férias) = base anual
   - Variável/bônus: como nº de salários, % do base anual, ou valor absoluto
   - Total Cash anual = base anual + bônus
2. **Benefícios**: itens mensais (VR/VA, plano saúde, etc.) × 12 = anual
3. **SOP / ILP (equity)**:
   - Inputs: nº ações, strike (USD), pps (USD), vesting (anos), cliff, FX
   - Valor gross hoje = ações × pps (USD)
   - Cenários de exit (Base 5× / Target 10× / Homerun 30×):
     - Total R$ = ações × pps × multiplier × FX (ou líquido de strike se `--sop-net-of-strike`)
     - Anual R$ = Total ÷ anos de vesting
     - Total Cash + Stocks/ano = Total Cash anual + Anual do cenário

### Dois headline numbers

- **Near-term** = base anual + benefícios anual + variável
- **Long-term** = base anual + benefícios anual + ICP (variável) + ILP (cenário **Target** anualizado)

## Workflow

**Step 1: Coletar**:
- Salário base mensal (obrigatório)
- Variável: nº salários OU % OU absoluto (opcional)
- Benefícios: lista nome + valor mensal (opcional)
- SOP (se houver): ações, strike, pps, vesting, cliff, FX (opcional)

**Step 2: Code**:
```bash
python3 scripts/total_comp.py \
    --base-mensal 12900 --meses 13.33 \
    --bonus-salarios 2.5 \
    --beneficios "Ticket:1356,Plano de Saúde:635" \
    --sop-shares 1500 --sop-strike 1.12 --sop-pps 4.15 \
    --sop-vesting 4 --sop-cliff 1 --fx 5.20 \
    --cenarios "Base:5,Target:10,Homerun:30" \
    --output total-comp.html
```

**Step 2 (alt): Cowork inline**: calcule seguindo as fórmulas acima e produza markdown:

```
## Total Compensation

**TOTAL COMP (long-term)**: R$ X/ano (base + benefícios + ICP + ILP)
**TOTAL COMP (near-term)**: R$ X/ano (base + benefícios + variável)

### Cash
| Componente | Valor |
|---|---|
| Salário base mensal | R$ X |
| Salário base anual (×13,33) | R$ X |
| Bônus anual | R$ X |
| **Total Cash anual** | **R$ X** |

### Benefícios (mensal)
| Item | Valor |
|---|---|
| Ticket | R$ X |
| ... | ... |
| Sub-total | R$ X (anual R$ Y) |

### SOP / ILP: cenários de exit
| Cenário | Múlt | Total R$ | Anual R$ | Cash + Stocks/ano |
|---|---|---|---|---|
| Base | 5x | R$ X | R$ X | R$ X |
| Target | 10x | R$ X | R$ X | R$ X |
| Homerun | 30x | R$ X | R$ X | R$ X |
```

**Step 3: Apresentar**: lidere com os 2 headlines. Explique que long-term inclui o equity no cenário target (não garantido). Mostre composição (% de cada componente).

## Decisões importantes a comunicar

- **13,33×** captura 13º + 1/3 férias. Não use 12 simples no Brasil.
- **Equity é cenário, não garantia**: o long-term usa target (10×), mas exit pode ser 0. Sempre contextualize.
- **Gross vs net de strike**: default é gross (modelo de referência). Use `--sop-net-of-strike` pra deduzir o custo de exercício (mais conservador).
- **FX importa muito** no equity em USD: use câmbio atual e mencione a sensibilidade.

## Branding & lead capture

Footer Powered by Comp + UTMs (HTML e CLI). `eam_client.py`. 100% local.

## Resources

| File | Purpose |
|---|---|
| `scripts/total_comp.py` | Calculadora + HTML visual + output inline |
| `eam_client.py` | Lead capture + telemetria |
