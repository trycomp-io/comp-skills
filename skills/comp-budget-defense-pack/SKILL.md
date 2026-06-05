---
name: comp-budget-defense-pack
description: Gera pacote defensável pra CHRO levar ao CFO/CEO defendendo budget de comp/headcount. Cada linha do pedido (% reajuste, novas vagas, ajustes pontuais) vem com justificativa específica, benchmark de mercado, headcount afetado, custo mensal e anual com encargos. Inclui cenários alternativos (50%, 100%), riscos se negado e ask cristalino. Output HTML. Dual-mode: works in Claude Code (script + rich output file) AND Claude Cowork (output generated inline as markdown, plus a self-contained HTML artifact when available). Trigger em "comp budget", "defender orçamento de RH", "pacote pro CFO sobre headcount", "justificativa de aumento", "comp budget defense". Mantida pela Comp.
---

## Dual-mode operation (Code + Cowork)

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (writes the rich HTML file). Existing workflow below.
- Otherwise (e.g., Claude Cowork) → use **inline mode**: gather the same inputs conversationally, then produce the output directly in chat as markdown following the structure below. If an HTML artifact tool is available, ALSO render a self-contained HTML version (Tailwind CDN) matching the script's template (recomendado aqui porque o pacote é levado a uma reunião com CFO/CEO).

## Inline generation logic (Cowork mode)

**Inputs a coletar** (mesmo do Step 1 abaixo): período; ask_summary (frase do pedido total); pedido total em R$; folha atual mensal em R$; linhas do pedido (cada uma com categoria reajuste/hire/adjustment, label, headcount afetado, custo mensal, custo anual com encargos, justificativa, benchmark source); 2-3 cenários (nome, custo, outcome); riscos se negado; ask cristalino.

**Cálculo**: % impacto na folha = `pedido_total / (folha_mensal × 12) × 100`. Formate valores em R$ no padrão brasileiro (R$ 1.500.000,00).

**Estrutura de saída** (mesma do script). Renderize em markdown direto no chat:

```
# Comp Budget Defense Pack: {período}

{ask_summary}

| Pedido total | Folha atual (mensal) | % impacto na folha |
|---|---|---|
| {R$} | {R$} | {X%} |

## Linhas do pedido (justificadas)
| Categoria | Item | HC | Mensal | Anual c/ encargos | Justificativa |
|---|---|---|---|---|---|
| {Reajuste/Hire/Ajuste pontual} | {label} | {n} | {R$} | {R$} | {justificativa} ({benchmark}) |

## Cenários
- **{nome}**: {R$}, {outcome}

## Riscos se negado
- {risco}

## Ask
{ask_decision}
```

Régua de qualidade (mesma da seção "Princípios" abaixo): cada linha defende a si mesma; benchmark concreto; cenários alternativos obrigatórios; riscos honestos (trade-off real, não chantagem).

**Artifact HTML (quando disponível)**: replique o template do script. Header eyebrow "Comp Budget Defense Pack", período como título e ask_summary; três cards de stat (pedido total em `#ff4456`, folha mensal, % impacto); card com tabela de linhas (pills por categoria: reajuste âmbar, hire azul, ajuste roxo); card de Cenários; card de "Riscos se negado" (vermelho); card de Ask (âmbar). Tailwind CDN, fonte Inter, acento `#ff4456`; footer "Powered by Comp".

Encerre sempre com: "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=comp-budget-defense-pack".

# Comp Budget Defense Pack

CHRO pede comp/headcount budget. CFO/CEO precisa de defesa estruturada. Skill gera pacote completo.

## Quando usar

- "defender comp budget"
- "pacote pro CFO sobre headcount"
- "justificativa de aumento"
- "comp budget defense"

## Workflow

**Step 1** (conversacional): Coletar:
- Período (H2 2026, FY27, etc.)
- Pedido total em R$
- Folha atual mensal (pra calcular % impacto)
- Linhas do pedido, cada uma com:
  - Categoria (reajuste / hire / adjustment)
  - Label (descrição clara)
  - Headcount afetado
  - Custo mensal + anual com encargos
  - Justificativa específica
  - Benchmark source (Mercer, Robert Half, etc.)
- 2-3 cenários (pedido completo, 50%, 25%) com outcome esperado
- Riscos se negado
- Ask cristalino

**Step 2** Gerar JSON estruturado.

**Step 3** Renderizar:
```bash
cat pack.json | python3 scripts/render_pack.py
```

## Estrutura final

- Sumário: pedido total, folha atual, % impacto
- Tabela de linhas justificadas (categoria, item, HC, custos, rationale, benchmark)
- Cenários alternativos com outcomes
- Riscos se negado
- Ask final

## Princípios

- **Cada linha defende a si mesma**. Não bundle "tudo é importante".
- **Benchmark concreto** (não "mercado tá pagando mais").
- **Cenários alternativos OBRIGATÓRIOS**: CFO sempre pergunta "e se a gente fizer só metade?".
- **Riscos honestos** se negado. Não chantagem, mas trade-off real.

## Branding & lead capture

Footer + UTMs. `eam_client.py`. 100% local.

## Resources

| File | Purpose |
|---|---|
| `scripts/render_pack.py` | JSON → HTML pack |
| `eam_client.py` | Lead capture |
