# Exit Survey Theme Analyzer

Transforma comentários abertos de entrevistas de desligamento e pesquisas de engajamento em **temas, sentimento e sinais acionáveis**.

A extração de temas é feita pelo agente (LLM) seguindo a metodologia da skill. O script Python apenas renderiza um relatório HTML a partir do JSON de temas produzido. O relatório traz:

- Temas rankeados por frequência (contagem + %)
- Sentimento por tema (negativo / neutro / positivo)
- Citações representativas anonimizadas
- Cruzamentos por segmento (área, tempo de casa, gestor)
- Flag de temas em alta negativa quando há datas

## Dual-mode

- **Claude Code**: o agente extrai os temas, monta o JSON e o script gera o HTML.
- **Claude Cowork**: o agente extrai os temas e produz markdown no chat, com artefato HTML quando disponível.

## Uso (Claude Code)

```bash
cat themes.json | python3 scripts/render_themes.py
```

O JSON de temas segue a estrutura documentada no `SKILL.md` (temas, frequência, sentimento, citações anonimizadas, segmentos, ações).

## Privacidade

- Citações sempre anonimizadas (sem nomes, cargos ou detalhes identificáveis).
- Células de segmento com menos de 3 comentários são suprimidas para evitar reidentificação em times pequenos.
- Processamento local.

---

Skill gratuita mantida pela [Comp](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=exit-survey-theme-analyzer), ferramentas para times de RH e People.
