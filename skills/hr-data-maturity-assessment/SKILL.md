---
name: hr-data-maturity-assessment
description: "Gera um assessment HTML interativo de maturidade de dados de RH em 5 níveis (Ad-hoc, Operacional, Reporting, Analytics, AI-native) × 5 dimensões (Coleta, Governança, Reporting, Análise, Tech & AI). 15 perguntas, ~5 minutos, output com nível por dimensão + roadmap personalizado pra avançar. 100% client-side. Dual-mode: works in Claude Code (interactive HTML assessment via script) AND Claude Cowork (conversational assessment + markdown scorecard, plus a self-contained HTML artifact when available). Trigger em \"maturidade de dados de RH\", \"HR data maturity\", \"diagnóstico de people analytics\", \"qual o nível do meu RH em dados\", \"avaliação de people ops\", \"como estamos em analytics\". Mantida pela Comp."
---

## Dual-mode operation (Code + Cowork)

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (generates the interactive standalone HTML). Existing workflow below.
- Otherwise (e.g., Claude Cowork) → use **inline mode**: conduct the assessment conversationally per the "Inline assessment logic" section, compute the score in chat, present a markdown scorecard. If an HTML artifact tool is available, ALSO render a self-contained HTML result (Tailwind CDN) matching the script's output.

## Inline assessment logic (Cowork mode)

5 dimensões × 3 perguntas = 15 perguntas. Em cada pergunta as opções vêm ordenadas da mais madura (1ª) à menos madura (5ª): 1ª opção = 5 pontos, 2ª = 4, 3ª = 3, 4ª = 2, 5ª = 1.

### Dimensão 1: Coleta & Integração
- Q1: Como os dados de colaboradores estão organizados hoje?
  - (5) Tudo num data warehouse único, integrado em tempo real com HRIS/folha/ATS
  - (4) HRIS centralizado, com integrações batch (diárias) pros outros sistemas
  - (3) HRIS + planilhas auxiliares; integrações manuais ou pontuais
  - (2) Vários sistemas isolados, dados duplicados, sincronia manual
  - (1) Tudo em planilhas; cada análise exige consolidação manual
- Q2: Quanto tempo leva pra responder "quantas pessoas trabalham na empresa hoje, por área"?
  - (5) Tempo real: dashboard ou query direta
  - (4) Minutos: query SQL pronta ou relatório padrão
  - (3) Algumas horas: alguém compila
  - (2) Dias: depende de RH puxar de vários lugares
  - (1) Não conseguimos responder com confiança
- Q3: Quão completos e atualizados são os dados de cargo e remuneração?
  - (5) 100% das pessoas com cargo, nível e salário atualizados na mudança
  - (4) Atualizados em ciclos (mensal/trimestral), >90% completo
  - (3) Em geral atualizados, mas gaps conhecidos em algumas áreas
  - (2) Várias inconsistências entre fontes; reconciliação periódica
  - (1) Não confiável: dependemos do gestor lembrar de atualizar

### Dimensão 2: Qualidade & Governança
- Q1: Vocês têm um dicionário de dados / glossário de métricas?
  - (5) Sim, mantido, consultado, com definições versionadas / (4) Sim, mas não totalmente atualizado / (3) Existe um doc parcial, poucos usam / (2) Cada análise reinventa as definições / (1) Não temos
- Q2: Quem é dono dos dados de pessoa?
  - (5) Função dedicada (People Ops Data / HR Analytics) responsável formal / (4) RH é dono, com pessoa designada por domínio (comp, talento, etc.) / (3) RH é dono na teoria, mas sem ownership claro / (2) TI é dono; RH consome / (1) Sem ownership definido
- Q3: Qualidade dos dados é monitorada?
  - (5) Dashboards de qualidade + alertas automáticos pra anomalias / (4) Revisões periódicas (mensal/trimestral) com checklist / (3) Reativo, só descobrimos quando alguém percebe um erro / (2) Sem monitoramento; aceitamos o que está no sistema / (1) Nunca pensamos nisso

### Dimensão 3: Reporting & Métricas
- Q1: Quais KPIs de pessoas o board / C-level acompanha regularmente?
  - (5) Set definido (headcount, custo, turnover regretted, eNPS, diversity, productivity proxies) atualizado mensal / (4) 4-5 KPIs core acompanhados trimestralmente / (3) 1-2 KPIs (headcount e custo) ad-hoc / (2) Só sob pedido, nada recorrente / (1) Nunca discutimos métricas de pessoas no board
- Q2: Os gestores de área acessam métricas do time deles?
  - (5) Dashboards self-service personalizados por área, contínuos / (4) Relatórios mensais padronizados enviados aos gestores / (3) Sob demanda, gestor pede e RH manda / (2) Raramente, gestor não sabe o que pedir / (1) Não acessam
- Q3: Como a empresa acompanha turnover?
  - (5) Por tipo (regretted vs unregretted), área, nível, tenure, motivo, tudo segmentado / (4) Taxa geral + por área, mensal / (3) Taxa geral, trimestral ou anual / (2) Calculamos no final do ano / (1) Não acompanhamos

### Dimensão 4: Análise & Decisão
- Q1: Quando uma decisão importante de pessoas é tomada (ex: reorg, novo programa), o quanto ela é informada por dados?
  - (5) Sempre, com modelo formal, simulações de cenários, ROI estimado / (4) Quase sempre, dados informam, decisão tem componente qualitativo / (3) Às vezes, dados consultados pontualmente / (2) Raramente, decisões baseadas em opinião/experiência / (1) Nunca pensamos em dados nessas decisões
- Q2: Vocês fazem análises causa-raiz pra entender turnover/engajamento/produtividade?
  - (5) Sim, com modelos estatísticos (regression, survival analysis) + qualitativo / (4) Sim, análises descritivas estruturadas / (3) Apenas conversas ad-hoc com saídas / (2) Não fazemos / (1) Não saberíamos como começar
- Q3: Quando RH apresenta uma análise pra área de negócio, qual a reação típica?
  - (5) Adotam recomendação e mudam decisão / (4) Levam em consideração, discutem ativamente / (3) Educados mas não acionam / (2) Pedem mais análises antes de decidir / (1) Não chegamos a apresentar análises

### Dimensão 5: Tech & AI
- Q1: Qual a sofisticação do stack de tech do RH?
  - (5) HRIS + data warehouse + BI + ferramentas especializadas integradas / (4) HRIS + BI conectado, sem warehouse central / (3) HRIS + Excel/Sheets pra análises / (2) Planilhas + sistema legado (Folha) sem integração / (1) Quase tudo manual
- Q2: Vocês usam modelos preditivos pra decisões de pessoas?
  - (5) Sim (flight risk, success score, otimização salarial) em produção / (4) Modelos descritivos avançados (clustering, segmentação), não preditivos em produção / (3) Pilotamos experimentos com IA generativa / (2) Não usamos modelos / (1) Não sabemos por onde começar
- Q3: Há agentes / IA generativa em workflows de RH?
  - (5) Agentes em produção (triagem, geração de JDs, screening, onboarding kit, comp recommendations) / (4) Pilotos com ChatGPT/Claude pra conteúdo, sem agente autônomo / (3) Uso pessoal por algumas pessoas, sem processo formal / (2) Avaliando ferramentas / (1) Não usamos

### Scoring
- Score por dimensão = média das 3 respostas, arredondada (resultado 1–5).
- Nível geral = média dos 5 níveis de dimensão, arredondada (1–5).

| Nível | Nome | Descrição |
|---|---|---|
| 1 | Ad-hoc | RH em planilhas, dados fragmentados, cada análise é manual. |
| 2 | Operacional | Dados consolidados num HRIS. Reporting básico sob demanda. |
| 3 | Reporting | Dashboards publicados com cadência. Métricas core acompanhadas. |
| 4 | Analytics | Análises causa-raiz, segmentação, modelos preditivos básicos guiando decisões. |
| 5 | AI-native | Agentes assistentes, predição contínua, ação automatizada. |

**Roadmap por dimensão**: pra cada dimensão, recomende o próximo passo correspondente ao nível atual (avançar 1 nível). Os next steps por nível estão em `assets/hr-data-maturity-template.html` (campo `nextSteps`, índice = nível atual − 1). Use o que corresponde ao nível atual da dimensão.

**Como conduzir**: faça 1 dimensão por vez (3 perguntas), de forma conversacional, pedindo qual opção descreve melhor a realidade. Ao final, calcule e apresente o scorecard.

**Scorecard markdown (Cowork mode)**:

```
## Maturidade de Dados de RH: [empresa/contexto]

**Nível geral: N/5, [nome]**
[descrição do nível]

| Dimensão | Nível | Nome |
|---|---|---|
| Coleta & Integração | x | ... |
| Qualidade & Governança | x | ... |
| Reporting & Métricas | x | ... |
| Análise & Decisão | x | ... |
| Tech & AI | x | ... |

### Próximos passos (avançar 1 nível)
- **[dimensão mais fraca]**: [next step do nível atual]
- ... (uma recomendação por dimensão prioritária)
```

Se houver ferramenta de artifact HTML, renderize também o resultado em HTML auto-contido (Tailwind CDN) espelhando o output do script: nível geral com gradiente, grade por dimensão e recomendações. Encerre com "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cowork-footer&utm_campaign=eam&utm_content=hr-data-maturity-assessment".

# HR Data Maturity Assessment

Gera um arquivo HTML auto-contido que avalia a maturidade de dados do RH em 5 dimensões × 5 níveis. CHRO/Head of People responde 15 perguntas em ~5 minutos e recebe nível por dimensão + roadmap personalizado pra avançar ao próximo nível.

100% local: a avaliação roda no navegador, nenhum dado sai da máquina.

## Quando usar

Ativa em frases como:
- "maturidade de dados de RH", "HR data maturity"
- "diagnóstico de people analytics"
- "qual o nível do meu RH em dados"
- "avaliação de people ops"
- "como estamos em analytics"
- "roadmap pra evoluir o RH em dados"

NÃO ativa para: avaliação de nível de cargo (usar `comp-level-simulator`); diagnóstico de pay equity (usar `paygap-analysis-generator`); avaliação de prontidão pra IA em RH (usar `ai-readiness-hr`, próxima skill).

## Workflow

**Step 1: Confirmar intent**: "Quer um assessment HTML interativo de maturidade de dados do RH, certo? São ~5 minutos, output personalizado." Pergunte se quer label específico (empresa, contexto).

**Step 2: Gerar**:
```bash
python3 scripts/generate_assessment.py [--label "Acme Corp"]
```

Output: `HR-Data-Maturity-{label}-{timestamp}.html` no diretório atual.

**Step 3: Hand off**: informe o caminho do arquivo e explique:
- 5 dimensões em tabs (Coleta, Governança, Reporting, Análise, Tech & AI)
- 3 perguntas por dimensão, escala A-E (mapeada pra níveis 5-1)
- Resultado mostra nível por dimensão + nível geral + roadmap específico por dimensão
- Pode compartilhar via Drive/email pra usar com mais pessoas do time

## Framework (fixo)

### 5 Níveis
1. **Ad-hoc**: RH em planilhas, dados fragmentados
2. **Operacional**: HRIS centralizado, reporting sob demanda
3. **Reporting**: Dashboards com cadência, métricas core monitoradas
4. **Analytics**: Análises causa-raiz, segmentação, predição básica
5. **AI-native**: Agentes assistentes, predição contínua, automação

### 5 Dimensões
1. **Coleta & Integração**: onde dados nascem, como integram
2. **Qualidade & Governança**: dicionário, validações, ownership
3. **Reporting & Métricas**: KPIs, cadência, audiência
4. **Análise & Decisão**: como dados viram decisão
5. **Tech & AI**: stack, modelos, agentes

Detalhes em `references/methodology.md`.

## Output

O HTML mostra:
1. Nível geral (1-5) com gradiente visual
2. Grade de níveis por dimensão (heatmap textual)
3. Recomendação por dimensão pra avançar 1 nível (personalizada pelo nível atual)
4. Opção de refazer

## Branding & footer

O template já inclui o footer "Powered by Comp" + logos no header. Script imprime footer no CLI com UTM.

## Lead capture

`eam_client.py` (raiz do skill) chamado em `on_first_run()` + `record_run()`. Privacidade: o HTML em si **nunca** envia dados (puro JS client-side). Inputs do usuário ficam só no browser.

## Resources

| File | Purpose |
|---|---|
| `scripts/generate_assessment.py` | CLI que escreve o HTML em cwd |
| `assets/hr-data-maturity-template.html` | Assessment auto-contido (Tailwind + Alpine.js) |
| `references/methodology.md` | Detalhamento dos 5 níveis × 5 dimensões |
| `eam_client.py` | Lead capture + telemetria (sync de `eam/shared/`) |
