---
name: ai-native-hr
description: Gera um assessment HTML interativo de prontidão para IA em RH, baseado no AI Maturity Map da Comp (https://comp.vc/ai-maturity-map). Avalia 5 níveis (N1 Produtividade Individual → N5 Inteligência Adaptativa) em 5 áreas de RH (Recrutamento, Compensação, L&D, People Ops, Analytics). Output: nível por área + alerta de dispersão + próxima fronteira + armadilhas frequentes. 15 perguntas, ~5 minutos, 100% client-side. Dual-mode: works in Claude Code (interactive HTML assessment via script) AND Claude Cowork (conversational assessment + markdown scorecard, plus a self-contained HTML artifact when available). Trigger em "maturidade de IA em RH", "AI readiness for HR", "qual o nível de IA do meu RH", "AI maturity map", "como está minha empresa em IA pra RH", "diagnóstico de IA no RH". Mantida pela Comp.
---

## Dual-mode operation (Code + Cowork)

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (generates the interactive standalone HTML). Existing workflow below.
- Otherwise (e.g., Claude Cowork) → use **inline mode**: conduct the assessment conversationally per the "Inline assessment logic" section, compute the score in chat, present a markdown scorecard. If an HTML artifact tool is available, ALSO render a self-contained HTML result (Tailwind CDN) matching the script's output.

## Inline assessment logic (Cowork mode)

5 áreas × 3 perguntas = 15 perguntas. As opções vêm ordenadas do nível mais maduro (1ª) ao menos maduro (5ª): 1ª opção = 5 (N5), 2ª = 4 (N4), 3ª = 3 (N3), 4ª = 2 (N2), 5ª = 1 (N1).

### Os 5 níveis (AI Maturity Map da Comp)
- N1 Produtividade Individual: pessoas usam IA pra ganhar produtividade no próprio trabalho. Variância alta entre power users e o resto.
- N2 Produtividade do Time: skills e agentes compartilhados cobrem a maior parte das tarefas operacionais.
- N3 Sistema Operacional Contextual: uma camada agêntica única executa trabalho complexo dentro de parâmetros humanos.
- N4 Inteligência de Decisão: camada agêntica propõe decisões baseada nos padrões dos melhores humanos.
- N5 Inteligência Adaptativa: camada agêntica aprende sozinha dos resultados, refinando julgamento continuamente.

### Área 1: Recrutamento & TA
- Q1: Como a IA aparece no recrutamento hoje? (5) Camada agêntica autônoma que aprende com sucesso pós-contratação / (4) IA recomenda candidatos/scores; humanos validam / (3) Um agente único cobre todo o pipeline integrado ao ATS / (2) Time compartilha skills/agentes (JD, follow-ups, summary) / (1) Recruiters usam ChatGPT/Claude pra tarefas pontuais
- Q2: Como vocês conseguem candidatos qualificados? (5) Sistema autoaprende a cada hire / (4) Modelo de matching gera shortlist; humano valida / (3) Um agente faz outreach + qualificação integrado ao CRM / (2) Skills compartilhadas pra outreach, qualificação manual / (1) Busca manual no LinkedIn com ajuda pontual de IA
- Q3: Tempo médio pra entrevistar um candidato qualificado depois de aberta a vaga? (5) Horas / (4) Dias (agentes fazem 80%) / (3) 1 semana / (2) 2-3 semanas / (1) 4+ semanas

### Área 2: Compensação & Rewards
- Q1: Como vocês calibram salários e propostas hoje? (5) Sistema autoaprende a cada hire/promoção / (4) IA recomenda salário; humano valida / (3) Agente único responde "qual o salário ideal pra X" / (2) Skills compartilhadas pra cálculos pontuais / (1) Comp manager usa ChatGPT/Claude individualmente
- Q2: Como o time toma decisões de mérito anual? (5) Recomendação automática contínua refinada por outcomes / (4) IA propõe distribuição; comitês validam / (3) Agente único entrega análise pré-calibração / (2) Planilhas + scripts ad-hoc / (1) 100% manual
- Q3: Quanto tempo leva uma análise de equidade salarial? (5) Contínua, sistema monitora e alerta / (4) Horas, sob demanda, com recomendação / (3) Dias, com agente sob comando / (2) Semanas, com scripts/skills / (1) Meses, manual em planilha

### Área 3: L&D / Performance
- Q1: Como a empresa gerencia ciclos de performance e feedback? (5) Sistema observa o trabalho e ajusta plano contínuo / (4) IA propõe rating + plano; humano valida / (3) Agente único orquestra o ciclo todo / (2) Skills compartilhadas pra partes do ciclo / (1) Manager usa ChatGPT/Claude pontualmente
- Q2: Como vocês decidem o que treinar (oferta de L&D)? (5) IA detecta gaps em tempo real e oferece micro-learning / (4) Modelo recomenda curadoria por pessoa / (3) Plataforma única responde o que cada um precisa / (2) Pesquisa anual + catálogo curado por área / (1) Catálogo genérico, colaborador escolhe
- Q3: Como managers preparam conversas de carreira / 1:1? (5) Sistema autônomo prepara dossier por 1:1 / (4) IA propõe agenda com tópicos críticos / (3) Agente único responde "o que discutir com X" / (2) Template + skill, preparação manual / (1) Manager prepara sozinho, sem IA

### Área 4: People Ops / Admin
- Q1: Como funciona onboarding hoje? (5) Agente autônomo personaliza por persona e aprende / (4) IA propõe 30/60/90 + checklist; People Ops valida / (3) Agente único orquestra tudo / (2) Skills compartilhadas pra partes / (1) Manual com templates
- Q2: Quem responde dúvidas operacionais (folha, férias, benefícios)? (5) Agente conversacional autônomo que aprende / (4) IA responde maioria, escala casos complexos / (3) Agente único conectado a tudo responde via chat / (2) FAQ + macros + IA pontual / (1) People Ops responde uma a uma
- Q3: Como processos repetitivos (mudança de dados, rescisão, comunicações em massa) são executados? (5) Agente autônomo executa e ajusta por outcome / (4) IA propõe a execução; People Ops valida / (3) Agente único coordena sistemas sob comando / (2) Skills automatizam tarefas; orquestração manual / (1) Tudo manual

### Área 5: People Analytics / Decisão
- Q1: Como dashboards e análises chegam aos decisores? (5) Sistema gera análises proativamente / (4) IA prepara análise + recomendação; humano valida / (3) Agente único responde qualquer pergunta conectado às fontes / (2) Skills rodam análises padrão; ad-hoc manual / (1) Analista roda relatório manual em Excel/BI
- Q2: Como respondem "qual o risco de turnover no time de eng"? (5) Sistema autoaprendendo monitora e alerta proativo / (4) IA gera score de risco + ação; gestor valida / (3) Agente único responde com modelo e segmentação / (2) Skills calculam métricas; causal manual / (1) People Analytics roda manualmente
- Q3: Que decisões executivas hoje são tomadas com base em recomendação direta de IA? (5) Várias (reorg, promoção, retenção) com sistema sugerindo / (4) Algumas decisões críticas já incorporam recomendação validada / (3) IA fornece análise robusta, decisão 100% humana / (2) IA ajuda em partes, raramente vai pra decisão / (1) Nenhuma

### Scoring
- Nível por área = média das 3 respostas, arredondada (1–5 → N1–N5).
- Nível geral = mediana dos 5 níveis de área (alinhado com "area-based progression").
- **Alerta de dispersão**: se (maior nível de área − menor nível de área) ≥ 2, sinalize: é sinal crítico do framework.

### Output por área
Pra cada área mostre nível atual, próxima fronteira (N+1) e a armadilha frequente daquela transição. Os textos exatos de fronteira e armadilha por nível estão em `assets/ai-native-hr-template.html` (campos `frontierByLevel` e `trapByLevel`, índice = `min(4, nível − 1)`). Use o texto correspondente ao nível atual da área.

**Princípios a reforçar**: backward planning (desenhar pro target desde o dia 0), area-based progression (levar o playbook das áreas mais maduras pras menos), closed-loop (aprovação humana sem integração de feedback ≠ aprendizado real).

**Como conduzir**: faça 1 área por vez (3 perguntas), de forma conversacional. Ao final, calcule níveis por área, a mediana geral, cheque a dispersão e apresente o scorecard.

**Scorecard markdown (Cowork mode)**:

```
## Maturidade de IA em RH: [empresa/contexto]

**Nível geral: NX [nome]** (mediana das áreas)
[alerta de dispersão se aplicável: "Dispersão alta entre áreas (X→Y). Leve o playbook das áreas mais maduras pras menos"]

| Área | Nível | Próxima fronteira | Armadilha |
|---|---|---|---|
| Recrutamento & TA | NX | ... | ... |
| Compensação & Rewards | NX | ... | ... |
| L&D / Performance | NX | ... | ... |
| People Ops / Admin | NX | ... | ... |
| People Analytics / Decisão | NX | ... | ... |
```

Se houver ferramenta de artifact HTML, renderize também o resultado em HTML auto-contido (Tailwind CDN) espelhando o output do script: nível geral, heatmap por área, alerta de dispersão, fronteira e armadilha por área. Encerre com "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cowork-footer&utm_campaign=eam&utm_content=ai-native-hr".

# AI Native HR Assessment

Gera um arquivo HTML que avalia a maturidade do RH em IA usando o [AI Maturity Map da Comp](https://comp.vc/ai-maturity-map?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=ai-maturity-map). 5 níveis × 5 áreas de RH, 15 perguntas em ~5 minutos.

100% local: a avaliação roda no navegador, nenhum dado sai da máquina.

## Quando usar

Ativa em frases como:
- "maturidade de IA em RH"
- "AI readiness for HR" / "AI maturity HR"
- "qual o nível de IA do meu RH"
- "como está minha empresa em IA pra RH"
- "diagnóstico de IA no RH"
- "AI Maturity Map da Comp"

NÃO ativa para: maturidade de DADOS (usar `hr-data-maturity-assessment`, frameworks diferentes); avaliação de nível de cargo (usar `comp-level-simulator`).

## Workflow

**Step 1: Confirmar intent**: "Quer o assessment de prontidão pra IA do RH baseado no AI Maturity Map da Comp? São ~5 minutos, avalia 5 áreas separadas."

**Step 2: Gerar**:
```bash
python3 scripts/generate_assessment.py [--label "Acme Corp"]
```

Output: `AI-Native-HR-{label}-{timestamp}.html` no diretório atual.

**Step 3: Hand off**: explique o que tem no relatório:
- Nível geral N1-N5 (mediana das áreas, alinhado com "area-based progression")
- Nível por área (5 áreas de RH)
- **Alerta de dispersão** se diferença de 2+ níveis entre áreas (sinal crítico do framework)
- Próxima fronteira por área (o que faz mover N → N+1)
- Armadilha frequente por área (erros típicos da transição)

## Framework Comp (fixo)

### 5 Níveis
- **N1 Produtividade Individual**: pessoas usam IA pra ganhar produtividade
- **N2 Produtividade do Time**: skills e agentes compartilhados
- **N3 Sistema Operacional Contextual**: camada agêntica única
- **N4 Inteligência de Decisão**: IA propõe decisões calibradas com top humanos
- **N5 Inteligência Adaptativa**: sistema aprende sozinho dos outcomes

### 5 Áreas de RH (avaliadas separadamente)
1. Recrutamento & TA
2. Compensação & Rewards
3. L&D / Performance
4. People Ops / Admin
5. People Analytics / Decisão

Detalhes em `references/methodology.md`.

## Princípios do framework reforçados no output

- **Backward planning**: design pro target level desde o dia 0, não escala incremental
- **Area-based progression**: áreas avançam separadamente, levando o playbook das mais maduras pras menos
- **Closed-loop**: aprovação humana sem integração de feedback ≠ aprendizado real
- **Armadilhas**: cada transição tem armadilha típica explicitada no report

## Branding & footer

O template tem footer "Powered by Comp" + logos no header + link UTM-tagueado pro AI Maturity Map original. Script imprime footer no CLI.

## Lead capture

`eam_client.py` (raiz do skill) é chamado em `on_first_run()` + `record_run()`. Privacidade: o HTML em si **nunca** envia dados.

## Resources

| File | Purpose |
|---|---|
| `scripts/generate_assessment.py` | CLI que escreve o HTML em cwd |
| `assets/ai-native-hr-template.html` | Assessment auto-contido (Tailwind + Alpine.js) |
| `references/methodology.md` | Framework completo da Comp + adaptação pra HR |
| `eam_client.py` | Lead capture + telemetria (sync de `eam/shared/`) |
