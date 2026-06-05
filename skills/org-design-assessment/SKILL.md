---
name: org-design-assessment
description: "Assessment HTML interativo de maturidade em design organizacional, baseado no framework Comp (artigo Cajuína \"Você confia milhões à intuição?\"). 4 pilares × 3 perguntas: Maturidade de Governança (CLT/PJ), Span of Control, Pirâmide de Níveis, Disparidade Salarial Interna. Output: Score 0-100 por pilar e geral, classificação (Reativo a Estratégico) e próximo passo personalizado por pilar. ~5 minutos. Dual-mode: works in Claude Code (interactive HTML assessment via script) AND Claude Cowork (conversational assessment + markdown scorecard, plus a self-contained HTML artifact when available). Trigger em \"maturidade de org design\", \"diagnóstico organizacional\", \"score de remuneração\", \"data-driven org design\", \"avaliar estrutura org\". Mantida pela Comp."
---

## Dual-mode operation (Code + Cowork)

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (generates the interactive standalone HTML). Existing workflow below.
- Otherwise (e.g., Claude Cowork) → use **inline mode**: conduct the assessment conversationally per a "Inline assessment logic" section, compute the score in chat, present a markdown scorecard. If an HTML artifact tool is available, ALSO render a self-contained HTML result (Tailwind CDN) matching the script's output.

## Inline assessment logic (Cowork mode)

4 pilares × 3 perguntas = 12 perguntas. As opções vêm ordenadas da mais madura (1ª) à menos madura (5ª): 1ª opção = 5 pontos, 2ª = 4, 3ª = 3, 4ª = 2, 5ª = 1.

### Pilar 1: Maturidade de Governança (modelos contratuais CLT/PJ/híbrido como alavanca)
- Q1: Como você decide entre CLT, PJ ou modelo híbrido pra uma nova contratação? (5) Política clara por função/nível + custo previsível + segurança jurídica documentada / (4) Política por função, exceções aprovadas pelo CFO/CHRO / (3) Caso a caso, jurídico quando há dúvida / (2) Caso a caso, na vontade do candidato ou hiring manager / (1) Sem política, improvisamos
- Q2: Você sabe o custo total empregador de cada modelo (encargos, passivos e risco de processo)? (5) Sim, modelo financeiro atualizado + provisão de risco por modalidade / (4) Sim, em planilha atualizada quando necessário / (3) Sabemos o cash mensal, não passivos futuros / (2) Sabemos só o salário base / (1) Sem visibilidade
- Q3: Qual o nível de risco jurídico-trabalhista exposto pela sua estrutura atual? (5) Mapeado, monitorado e mitigado proativamente / (4) Mapeado, mitigação reativa / (3) Reconhecemos riscos mas não mapeamos / (2) Descobrimos quando aparecem ações / (1) Não fazemos ideia

### Pilar 2: Span of Control (densidade e eficácia de liderança)
- Q1: Você consegue dizer quantos diretos cada gestor da empresa tem agora? (5) Tempo real, dashboard com outliers / (4) Sob demanda em minutos, query no HRIS / (3) Em horas, alguém compila / (2) Em dias, esforço manual / (1) Não conseguimos
- Q2: Já mediu o "custo de gestão" (% folha com managers vs ICs)? (5) Sim, com benchmark e meta / (4) Sim, em momentos pontuais / (3) Entendemos conceitualmente, sem número / (2) Nunca medimos / (1) Não entendo a métrica
- Q3: Identifica gestores sobrecarregados (15+ diretos) e subutilizados (1-3 diretos) hoje? (5) Sim, revisão semestral + action plan por outlier / (4) Sim, no planejamento anual / (3) Os mais óbvios em conversa / (2) Sem visão estruturada / (1) Não pensamos nisso

### Pilar 3: Pirâmide de Níveis (composição operacional/especialista/liderança)
- Q1: Como sua pirâmide atual compara com sua estratégia de 3-5 anos? (5) Gap formal + plano de hiring e mobilidade / (4) Discussão estratégica anual com ajustes / (3) Conhecemos a pirâmide, sem atrelar à estratégia / (2) Nunca mapeamos formalmente / (1) Não sei dizer minha pirâmide hoje
- Q2: Você tem benchmark da pirâmide do seu setor / estágio? (5) Sim, painel definido + revisão regular / (4) Sim, em alguns momentos / (3) Já vi referências, sem comparação formal / (2) Não temos / (1) Não sabia que existia
- Q3: Como você decide promover vs contratar externamente? (5) Análise de bench interno + market premium + sucessão / (4) Caso a caso com input de RH / (3) Decisão do hiring manager / (2) Default no externo / (1) Sem critério

### Pilar 4: Disparidade Salarial Interna (equidade, faixa ideal 80%-120% da mediana por nível)
- Q1: Você sabe a dispersão salarial dentro de cada nível (min-mediana-max)? (5) Sim, dashboard com alertas pra outliers / (4) Sim, relatórios trimestrais / (3) Sob demanda, com esforço / (2) Sem visibilidade clara / (1) Não calculamos por nível
- Q2: Quantos colaboradores estão fora da faixa 80%-120% da mediana do nível? (5) Sei o número, com plano por outlier / (4) Sei aproximadamente, sem ação / (3) Já vi, sem revisão regular / (2) Não medimos / (1) Não tem mediana definida
- Q3: Hires externos entram com salário diferente da banda dos pares internos? (5) Não, política rígida, exceções excepcionais / (4) Raramente, exceções aprovadas pelo CHRO / (3) Acontece, tentamos mitigar / (2) Acontece com frequência, sem plano / (1) É a regra: externo sempre paga mais

### Scoring
- Score por pilar = média das 3 respostas × 20 (resultado 0–100).
- Score geral = média dos 4 scores de pilar (0–100).

| Score | Classificação |
|---|---|
| 0–40 | Reativo (decisões na intuição) |
| 41–60 | Inicial (alguma estrutura) |
| 61–75 | Maduro (decisões informadas por dados) |
| 76–90 | Avançado (data-first, revisão contínua) |
| 91–100 | Estratégico (org design como alavanca de negócio) |

**Próximo passo por pilar**: recomende o passo correspondente ao nível atual de cada pilar. Os textos exatos estão em `assets/org-design-template.html` (campo `recommendations` por pilar, índice = média arredondada do pilar − 1).

**Como conduzir**: faça 1 pilar por vez (3 perguntas), de forma conversacional. Ao final, calcule scores e apresente o scorecard.

**Scorecard markdown (Cowork mode)**:

```
## Maturidade de Org Design: [empresa/contexto]

**Score geral: XX/100 ([classificação])**

| Pilar | Score | Classificação |
|---|---|---|
| Maturidade de Governança | xx | ... |
| Span of Control | xx | ... |
| Pirâmide de Níveis | xx | ... |
| Disparidade Salarial Interna | xx | ... |

### Próximos passos por pilar
- **[pilar]**: [recomendação do nível atual]
- ...
```

Se houver ferramenta de artifact HTML, renderize também o resultado em HTML auto-contido (Tailwind CDN) espelhando o output do script: score geral com barra, score por pilar e próximos passos. Encerre com "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cowork-footer&utm_campaign=eam&utm_content=org-design-assessment".

# Org Design Maturity Assessment

Gera um HTML interativo que avalia maturidade de design organizacional em 4 pilares (Governança, Span of Control, Pirâmide de Níveis, Disparidade Salarial). Output: Score 0-100 + classificação + próximos passos.

Baseado no [artigo Cajuína "Você confia milhões à intuição?"](https://cajuina.org/principais/coluna-comp/design-organizacional/).

## Quando usar

Ativa em frases como:
- "maturidade de org design"
- "diagnóstico organizacional"
- "score de remuneração" / "score de design org"
- "data-driven org design"
- "avaliar estrutura org"
- "como meu RH está em design organizacional"

NÃO ativa para: análise de span específica (usar `span-of-control-diagnostic`); maturidade de DADOS de RH (usar `hr-data-maturity-assessment`); maturidade em IA (usar `ai-native-hr`).

## Workflow

**Step 1**: Confirme intent: "Avaliação do design organizacional em 4 pilares, ~5 min."

**Step 2**: Rode `python3 scripts/generate_assessment.py [--label "Acme"]`. Output em cwd.

**Step 3**: Hand off, explique:
- 4 pilares (Governança, Span, Pirâmide, Spread)
- Score 0-100 por pilar + geral
- Classificação: Reativo / Inicial / Maduro / Avançado / Estratégico
- Próximo passo específico por pilar

## Framework Comp (fixo)

| Pilar | O que avalia |
|---|---|
| Maturidade de Governança | Modelos contratuais (CLT/PJ/híbrido) como alavanca |
| Span of Control | Densidade e eficácia de liderança |
| Pirâmide de Níveis | Composição força (operacional, especialista, liderança) |
| Disparidade Salarial Interna | Equidade interna (faixa 80%-120% mediana) |

Detalhes em `references/methodology.md`.

## Branding

Template tem footer "Powered by Comp" + link UTM-tagueado pro artigo.

## Resources

| File | Purpose |
|---|---|
| `scripts/generate_assessment.py` | Gera HTML em cwd |
| `assets/org-design-template.html` | Assessment auto-contido (Tailwind + Alpine.js) |
| `references/methodology.md` | 4 pilares + classificação 0-100 |
