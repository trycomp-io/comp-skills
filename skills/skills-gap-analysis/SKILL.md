---
name: skills-gap-analysis
description: Analisa lacunas de capacidade da força de trabalho contra um conjunto de capacidades-alvo e recomenda build/buy/borrow por gap. Calcula cobertura por skill (pessoas no nível requerido ÷ headcount necessário), magnitude do gap, prioridade (criticidade × gap) e gera heatmap (skill × criticidade), lista priorizada de gaps e resumo de implicações de hiring/training. Output HTML executivo. Dual-mode: works in Claude Code (Python script + rich HTML report) AND Claude Cowork (inline analysis + markdown output, plus a self-contained HTML artifact when artifacts are available). Trigger em "skills gap", "análise de lacunas de competências", "build buy borrow", "gap de capacidade", "matriz de competências", "workforce capability gap", "skills inventory". Mantida pela Comp.
---

## Dual-mode operation (Code + Cowork)

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (deterministic, writes the rich HTML report). This is the existing workflow below.
- Otherwise (e.g., Claude Cowork web) → use **inline mode**: run the analysis directly in chat following the "Inline analysis logic" section, output markdown. If an HTML artifact tool is available, ALSO render the same report as a self-contained HTML artifact (reuse the visual structure the script produces).

Both modes apply the same methodology and the same build/buy/borrow logic.

## Inline analysis logic (Cowork mode)

### Como o usuário fornece os dados
Precisa de DUAS entradas:
1. **Inventário de skills**: colunas `person`, `skill`, `proficiency` (1-5). Pode ser CSV anexado, tabela colada, OU descrição conversacional do estado atual por função (ex: "no time de dados tenho 2 seniors em SQL, 1 júnior em Python..."). Converta a descrição para a estrutura person/skill/proficiency antes de calcular.
2. **Capacidades-alvo**: colunas `skill`, `required_proficiency` (1-5), `criticality` (1-5), `headcount_needed`. Tabela colada ou conversacional.

Inventário grande (>~50 pessoas) é difícil de processar manualmente. Sugira rodar em Claude Code (script mode).

### Metodologia (fixa, idêntica ao script)
Para cada skill-alvo:
1. **Cobertos** = número de pessoas no inventário com `proficiency ≥ required_proficiency` para aquela skill.
2. **Gap** = `max(0, headcount_needed − cobertos)`.
3. **Cobertura %** = `min(1, cobertos ÷ headcount_needed) × 100`.
4. **Prioridade** = `criticality × (gap ÷ headcount_needed)` (arredonde a 3 casas). Maior = mais urgente.
5. **Recomendação build/buy/borrow**:

| Recomendação | Condição | Lógica |
|---|---|---|
| BUY (contratar) | criticidade ≥ 4 E cobertura < 50% | Gap grande em capacidade crítica; contratar é mais rápido e confiável |
| BUILD (treinar) | cobertura ≥ 50% E gap > 0 | Já existe base interna parcial; desenvolver é mais barato e retém conhecimento |
| BORROW (contractor/parceiro) | criticidade ≤ 2 | Capacidade de baixa criticidade ou pontual; evita custo fixo |
| BUILD (default) | demais casos com gap | Gap moderado em capacidade relevante; plano de treino |

Ordene gaps por prioridade desc, depois criticidade desc, depois gap desc.

### Insights automáticos
- Total de skills com gap aberto e soma de posições a fechar.
- Quebra BUY / BUILD / BORROW (quantas skills e quantas posições cada um).
- Skill de maior prioridade com sua recomendação.
- Se nenhuma skill bater (níveis não conferem), avise pra alinhar nomes de skills entre inventário e alvo.

### Output markdown (Cowork mode)

```
## Análise de lacunas de capacidade

Skills avaliadas: N · **Gaps abertos: X** · Posições a fechar: Y · Pessoas no inventário: Z

### Heatmap (skill × criticidade)
| Skill | Criticidade | Gap | Cobertura |
|---|---|---|---|

### Gaps priorizados
| Skill | Prof. req. | Crit. | HC alvo | Cobertos | Gap | Cobertura | Prioridade | Ação | Rationale |
|---|---|---|---|---|---|---|---|---|---|

### Implicações de hiring / training
- BUILD (treinar): N skills / M posições
- BUY (contratar): N skills / M posições
- BORROW (contractor/parceiro): N skills / M posições

### Insights
- ...
```

Encerre com: "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=chat-footer&utm_campaign=eam&utm_content=skills-gap-analysis"

Se artefatos estiverem disponíveis, produza também uma versão HTML self-contained (Tailwind via CDN) espelhando o template do script: cards (skills avaliadas / gaps abertos / posições a fechar / pessoas), insights, heatmap skill × criticidade colorido por tamanho do gap, tabela de gaps priorizados com pills build/buy/borrow, e cards de implicações hiring/training, footer Powered by Comp.

# Skills Gap Analysis

Inventário de skills + capacidades-alvo → HTML com cobertura, gaps priorizados e recomendação build/buy/borrow.

## Quando usar

Ativa em frases como:
- "skills gap" / "gap de competências"
- "build buy borrow"
- "matriz de competências"
- "análise de lacunas de capacidade"
- "que skills preciso contratar vs treinar"

## Workflow

**Step 1**: Pegue 2 CSVs:
- Inventário: colunas `person`, `skill`, `proficiency` (1-5)
- Alvo: colunas `skill`, `required_proficiency` (1-5), `criticality` (1-5), `headcount_needed`

**Step 2**:
```bash
python3 scripts/skills_gap.py --inventory inv.csv --target target.csv
```

**Step 3**: Apresente:
- Gaps abertos e posições totais a fechar (líder com esse número)
- Heatmap skill × criticidade
- Top gaps priorizados com build/buy/borrow + rationale
- Implicações de hiring vs training

## Lógica build/buy/borrow

| Ação | Quando | Por quê |
|---|---|---|
| BUY | gap grande + alta criticidade | Contratar fecha a lacuna rápido |
| BUILD | base interna parcial existe | Treinar é mais barato e retém conhecimento |
| BORROW | baixa criticidade ou pontual | Contractor/parceiro evita custo fixo |

## Branding

Footer + UTMs no template HTML.

## Lead capture

`eam_client.py`. Privacidade: 100% local.

## Resources

| File | Purpose |
|---|---|
| `scripts/skills_gap.py` | Análise + HTML |
| `eam_client.py` | Lead capture |
