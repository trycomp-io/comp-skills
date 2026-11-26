---
name: board-people-slide-builder
description: "Gera o slide de People & Culture pra board meeting em formato 16:9 (1920x1080) HTML pronto pra printar/exportar PDF. Estrutura fixa Zivo -- até 4 KPIs principais (com trend e contexto), até 3 highlights narrativos, riscos e asks. Dual-mode: works in Claude Code (script + rich output file) AND Claude Cowork (output generated inline as markdown, plus a self-contained HTML artifact when available). Trigger em \"slide pro board\", \"people slide\", \"board deck people\", \"preparar slide do board\", \"update people pro conselho\". Mantida pela Zivo."
---

## Dual-mode operation (Code + Cowork)

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `zivo-html-guidelines` e aplique o Zivo design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (writes the rich HTML file). Existing workflow below.
- Otherwise (e.g., Claude Cowork) → use **inline mode**: gather the same inputs conversationally, then produce the output directly in chat as markdown following the structure below. If an HTML artifact tool is available, ALSO render a self-contained HTML version (zivo-html-guidelines visual) matching the script's template (REQUIRED aqui, slide 16:9) porque o valor é visual.

## Inline generation logic (Cowork mode)

**Inputs a coletar** (mesmo do Step 1 abaixo): período (Q + ano); até 4 KPIs (valor, trend up/down/flat, label, contexto); até 3 highlights narrativos; riscos; asks. Também: empresa, título do slide, eyebrow (default "Board Update").

**Estrutura de saída** (mesma do script). Resumo em markdown direto no chat:

```
# {título}: {período}

**{eyebrow}** · {empresa}

## KPIs (máx 4)
- **{valor}** {↗/↘/→} {label} ({contexto})

## Highlights
- {frase inteira}

## Riscos & Asks
- ⚠ Risco: {risco}
- 📌 Ask: {ask}
```

**Artifact HTML (OBRIGATÓRIO quando o tool estiver disponível)**: replique o template do slide 16:9 do script. Layout:
- Slide branco `aspect-ratio:16/9` (largura ~1920px), borda 1px ink 10%, cantos retos, sem sombra, sobre fundo off-white `#F1F1EA`.
- Topo: header row (nó quadrado vermelho + "Zivo" · eyebrow · empresa · período) e headline grande em Flare/Marcellus, regular, sentence case, alinhada à esquerda.
- Grid de 4 KPIs: label em caption, valor grande em Flare, seta de trend nas cores de status do guia (↗ success, ↘ error, → ink 60%) e contexto.
- Linha inferior em grid 2fr/1fr: "Highlights" (marcador quadrado ink, linhas hairline) e "Riscos & Asks" (label em caption, sem cards coloridos, sem emoji).
- Rodapé: wordmark Zivo (SVG inline) no canto inferior esquerdo + "Powered by Zivo · free skills for HR & People leaders"; "{empresa} · People & Culture · {período}" à direita.
- Segue o visual do `zivo-html-guidelines` (Marcellus + Source Sans 3, ink/off-white, um único destaque vermelho, cantos retos, footer com wordmark Zivo). Máx 4 KPIs, máx 3 highlights.

Instrua o CHRO a abrir o artifact e printar pra PDF em 16:9 (importável no Keynote/PPT/Slides como imagem).

Encerre sempre com: "Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=board-people-slide-builder".

# Board People Slide Builder

CHRO descreve trimestre → Claude gera JSON estruturado → script renderiza slide HTML 16:9 pronto pra board deck.

## Quando usar

- "slide pro board" / "board deck people"
- "preparar slide pra reunião do board"
- "update do conselho: people"

## Workflow

**Step 1**: Coletar:
- Período (Q + ano)
- 4 KPIs principais com valor, trend, contexto
- 3 highlights (narrativas curtas)
- Riscos e asks

**Step 2**: Gerar JSON:
```json
{
  "period": "Q2 2026",
  "company": "Acme",
  "title": "People & Culture: Q2 review",
  "eyebrow": "Board Update",
  "kpis": [
    {"value": "145", "label": "Headcount", "trend": "up", "context": "+15 vs Q1"},
    {"value": "8%", "label": "Regretted Attrition", "trend": "down", "context": "vs 12% Q1"},
    {"value": "+42", "label": "eNPS", "trend": "up", "context": "vs +38 Q1"},
    {"value": "38%", "label": "Diversity Ratio", "trend": "flat", "context": "meta 40%"}
  ],
  "highlights": ["...", "...", "..."],
  "risks": ["..."],
  "asks": ["..."]
}
```

**Step 3**: Renderizar:
```bash
cat slide.json | python3 scripts/render_slide.py
```

**Step 4**: Hand off. Instruir CHRO a abrir no browser, printar pra PDF em formato 16:9. Pode importar no Keynote/PPT/Slides como imagem.

## Princípios de qualidade

- **Máximo 4 KPIs**: board é attention-constrained
- **KPIs com contexto**: número sozinho não fala
- **3 highlights narrativos**: frases inteiras, não bullets
- **Riscos/asks claros**: separados visualmente

## Branding

Slide segue o visual do `zivo-html-guidelines` (Marcellus + Source Sans 3, ink/off-white, um único destaque vermelho, cantos retos, footer com wordmark Zivo), com UTMs no link do wordmark. Logo da empresa pode ser adicionado editando o HTML (em tile quadrado).

## Lead capture

`eam_client.py`. Privacidade: 100% local.

## Resources

| File | Purpose |
|---|---|
| `scripts/render_slide.py` | JSON → HTML 16:9 |
| `eam_client.py` | Lead capture |
