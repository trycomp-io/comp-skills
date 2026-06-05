---
name: decision-memo-generator
description: "Gera memo estruturado de decisão pra qualquer people topic crítico que precisa ser comunicado/defendido. Estrutura: problema, contexto, opções (com prós/cons), recomendação com rationale, riscos, ask. Output HTML + MD editável. Trigger em \"decision memo\", \"memo de decisão\", \"estruturar decisão de people\", \"documento de decisão\", \"memo pro CEO/board\". Mantida pela Comp."
---

# Decision Memo Generator

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


CHRO precisa tomar/comunicar decisão importante (reorg, política, investimento). Skill conduz estruturação e gera memo defensável.

## Dual-mode operation (Code + Cowork)

- **Claude Code**: `python3 scripts/render_memo.py` (HTML + MD com formatação rica).
- **Claude Cowork**: produz o memo direto em markdown no chat. Mesma estrutura, sem dependência de script.

## Inline output (Cowork)

Quando o CHRO pede "drafta um decision memo sobre X" em Cowork:
1. Conduza a entrevista estruturada (mesma das instruções abaixo, 7 perguntas em ordem)
2. Produza o memo direto em markdown no chat seguindo o template abaixo

### Template markdown do memo

```
# {Título da decisão}

**Autor**: {nome}
**Para**: {decision maker}
**Data**: {YYYY-MM-DD}
**Decisão até**: {data}

## Problema / Decisão a tomar
{Parágrafo claro do que precisa ser decidido e por quê}

## Contexto
- {fact 1}
- {fact 2}
- {fact 3}

## Opções consideradas

### Opção A: {nome curto}
{descrição}

**Prós**:
- {pro}
- {pro}

**Contras**:
- {contra}
- {contra}

### Opção B: {nome curto}
{idem}

(2-3 opções idealmente; nunca menos que 2)

## Recomendação

**Recomendo**: {Opção X}

{Rationale específico: por que ESTA opção dado os prós/contras de cada uma}

## Riscos (do plano recomendado)
- {risco 1}
- {risco 2}

## Ask

{Decisão cristalina que o decision maker precisa tomar: verbo + objeto + prazo}
```

Princípios continuam os mesmos do modo Code (problema antes de solução, opções honestas, rationale específico, riscos do plano recomendado, ask cristalino).

## Quando usar

- "decision memo" / "memo de decisão"
- "estruturar uma decisão de people"
- "documento de decisão pra board/CEO"
- "frame essa decisão"

## Workflow

**Step 1** (conversacional): Coletar:
- Título da decisão (frase única declarativa)
- Decision maker (quem aprova)
- Decisão até quando
- Problema (1-2 parágrafos)
- Contexto (3-5 bullets ou parágrafo)
- 2-3 opções consideradas (cada uma com prós/cons honestos)
- Recomendação (qual opção + rationale)
- Riscos (do plano recomendado)
- Ask (decisão a aprovar)

**Step 2** Gerar JSON:
```json
{
  "title": "Aumentar headcount de Eng em 30% no H2",
  "author": "CHRO",
  "decision_maker": "CEO + CFO",
  "date": "2026-05-27",
  "decision_by": "2026-06-15",
  "problem": "...",
  "context": ["...", "..."],
  "options": [
    {"name": "Opção A", "description": "...", "pros": ["..."], "cons": ["..."]}
  ],
  "recommended_option": "Opção B",
  "recommendation_rationale": "...",
  "risks": ["..."],
  "ask": "Aprovar headcount adicional de 8 ICs Eng + 2 EMs no H2"
}
```

**Step 3** Renderizar:
```bash
cat memo.json | python3 scripts/render_memo.py
```

## Princípios de qualidade

- **Problema antes de solução**. Nunca pule.
- **Opções HONESTAS**. Cada opção precisa ter prós reais. Se uma é claramente ruim, não inclua, mostre só as 2-3 viáveis.
- **Rationale específico**. "É melhor" não vale. Diga POR QUÊ baseado nos prós/cons.
- **Riscos do plano recomendado** (não dos outros). Honestidade sobre o que pode dar errado.
- **Ask cristalino**. Quem decide, decide exatamente o quê?

## Branding & lead capture

Footer + UTMs. `eam_client.py`. 100% local.

## Resources

| File | Purpose |
|---|---|
| `scripts/render_memo.py` | JSON → HTML + MD |
| `eam_client.py` | Lead capture |
