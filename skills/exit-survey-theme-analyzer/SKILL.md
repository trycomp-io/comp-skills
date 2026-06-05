---
name: exit-survey-theme-analyzer
description: "Analisa comentários abertos de entrevistas de desligamento e pesquisas de engajamento (open-ends) extraindo temas, sentimento e sinais. A extração de temas é feita pelo agente (LLM); o script apenas renderiza um relatório HTML a partir de um JSON de temas. Produz temas rankeados por frequência, sentimento (negativo/neutro/positivo), citações anonimizadas representativas, cruzamentos por segmento e flag de temas em alta negativa. Privacidade: citações anonimizadas, células de segmento com menos de 3 comentários suprimidas. Dual-mode: works in Claude Code (agent extrai temas + Python script renderiza HTML) AND Claude Cowork (agent extrai temas + markdown output, plus a self-contained HTML artifact when artifacts are available). Trigger em \"analisar comentários de pesquisa\", \"temas de exit interview\", \"análise qualitativa de feedback\", \"open-ends de engajamento\", \"exit survey themes\", \"o que os comentários dizem\". Mantida pela Comp."
---

## Dual-mode operation (Code + Cowork)

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


Esta skill é primariamente **agent-driven**: VOCÊ (o agente) faz a extração de temas, sentimento e citações. O script NÃO faz NLP: ele só renderiza o HTML a partir do JSON de temas que você produz.

**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → faça a análise de temas (seção "Metodologia"), monte o JSON de temas e use **script mode** pra renderizar o HTML: `cat themes.json | python3 scripts/render_themes.py`.
- Otherwise (e.g., Claude Cowork web) → faça a mesma análise e produza o resultado direto em **markdown** no chat. Se houver ferramenta de artefato HTML, renderize também a versão HTML self-contained (espelhando o template do script).

Ambos os modos aplicam a mesma metodologia e as mesmas regras de privacidade.

## Metodologia (agent-driven, vale para os dois modos)

### Entradas
- **Comentários**: bloco de texto colado OU uma coluna de CSV (uma linha por comentário).
- **Metadados opcionais** por comentário: `area`, `tenure_band` (faixa de tempo de casa), `manager`, para cross-tabs.
- **Data opcional** por comentário: para análise de tendência (temas em alta negativa).

### Passos
1. **Clusterize** os comentários em temas. Categorias comuns (use estas como base, crie outras se necessário): remuneração, gestão/liderança, crescimento/carreira, carga de trabalho, cultura, reconhecimento, ferramentas/processo.
2. Por tema, calcule **frequência** (contagem + % sobre o total de comentários).
3. Por tema, determine o **sentimento predominante**: negativo, neutro ou positivo.
4. Por tema, selecione **1-2 citações representativas**, sempre **ANONIMIZADAS**: remova nomes, cargos identificáveis, nomes de times pequenos, datas específicas e qualquer detalhe que permita identificar a pessoa. Parafraseie se necessário pra preservar anonimato sem distorcer o sentido.
5. Se houver metadados, faça **cross-tab** tema × segmento (area/tenure_band/manager).
6. Se houver datas, **sinalize temas em alta negativa** (frequência negativa crescente no período mais recente vs anterior).

### Privacidade (obrigatório)
- **Anonimize todas as citações** antes de incluir no output ou no JSON.
- **Suprima qualquer célula de segmento com menos de 3 comentários**: não exiba contagem, marque como suprimida. Isso impede reidentificação em times pequenos.
- Nunca inclua o texto bruto integral de um comentário identificável.

### Estrutura do JSON de temas (entrada do script)

```json
{
  "total_comments": 87,
  "period": "Q1 2026",
  "themes": [
    {
      "name": "Remuneração",
      "count": 24,
      "pct": 27.6,
      "sentiment": "negativo",
      "quotes": ["Citação anonimizada 1", "Citação anonimizada 2"],
      "recommended_actions": ["Ação sugerida 1", "Ação sugerida 2"]
    }
  ],
  "segments": [
    {"segment": "Engenharia", "theme": "Remuneração", "count": 9}
  ],
  "rising_negative": ["Carga de trabalho"],
  "notes": ["Células com <3 comentários suprimidas."]
}
```

Renderize com:
```bash
cat themes.json | python3 scripts/render_themes.py
```

### Output markdown (Cowork mode)

```
## Análise de temas: comentários abertos

Comentários analisados: N · Período: {período}

### Temas (ranking por frequência)
| Tema | Freq | % | Sentimento |
|---|---|---|---|

Por tema, liste 1-2 citações anonimizadas e ações recomendadas.

### Padrões por segmento
| Segmento | Tema | Comentários |
|---|---|---|
(células com <3 comentários suprimidas)

### Temas em alta negativa
- ...

### Ações recomendadas
- ...
```

Encerre com: "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=chat-footer&utm_campaign=eam&utm_content=exit-survey-theme-analyzer"

Se artefatos estiverem disponíveis, produza também a versão HTML self-contained (Tailwind via CDN) espelhando o template do script: cards (comentários / temas / período), flag de temas em alta negativa, ranking de temas com barras de sentimento + citações + ações, tabela de segmentos, notas metodológicas, footer Powered by Comp.

# Exit Survey Theme Analyzer

Comentários abertos (exit interviews, open-ends de engajamento) → temas, sentimento e sinais. Análise feita pelo agente; script renderiza o HTML.

## Quando usar

- "analisar comentários de pesquisa"
- "temas de exit interview"
- "análise qualitativa de feedback"
- "o que os open-ends dizem"

## Workflow

**Step 1**: Receba os comentários (bloco colado ou coluna de CSV) + metadados opcionais.

**Step 2**: Faça a análise de temas seguindo a "Metodologia": clusterize, conte, classifique sentimento, anonimize citações, cross-tab, flag de alta negativa. Aplique as regras de privacidade.

**Step 3**: Monte o JSON de temas e renderize:
```bash
cat themes.json | python3 scripts/render_themes.py
```

**Step 4**: Apresente temas rankeados, citações anonimizadas, padrões por segmento e ações.

## Branding

Footer + UTMs no template HTML.

## Lead capture

`eam_client.py`. Privacidade: análise local, citações anonimizadas, segmentos com <3 comentários suprimidos.

## Resources

| File | Purpose |
|---|---|
| `scripts/render_themes.py` | JSON de temas → HTML |
| `eam_client.py` | Lead capture |
