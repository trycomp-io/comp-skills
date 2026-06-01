# Comp Skills

Skills gratuitos do Claude para líderes de RH & People, criados e mantidos pela [Comp](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=mirror-readme-intro).

**Versão atual: v0.6.3.** 37 skills, **todos** funcionam em Claude Code e Claude Cowork. [Ver release →](https://github.com/trycomp-io/comp-skills/releases/latest)

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

Instala os 37 skills de uma vez. Eles são model-invoked: basta descrever o que você quer e o Claude escolhe o skill certo (ex: "analisa o pay gap dessa planilha" aciona o `paygap-analysis-generator`).

Depois de instalar, rode `/reload-plugins` pra ativar.

## O que tem aqui (37 skills)

### Calculadoras (7)

| Skill | O que faz |
|---|---|
| [pj-vs-clt-calculator](skills/pj-vs-clt-calculator/) | Equivalência salarial CLT ↔ PJ com cálculo fiscal completo (INSS, IRPF, FGTS, 13º, férias, benefícios). Single ou batch via CSV. |
| [total-comp-calculator](skills/total-comp-calculator/) | Pacote completo de Total Compensation: cash (base + variável) + benefícios + equity (SOP/ILP com cenários). 2 headlines + visão visual. |
| [custo-demissao-calculator](skills/custo-demissao-calculator/) | Custo de rescisão CLT decomposto (saldo, aviso, 13º, férias, FGTS, INSS, IRPF) nos 4 tipos de demissão. |
| [custo-turnover-calculator](skills/custo-turnover-calculator/) | Custo real (oculto) de turnover em 8 componentes. Quick mode (multiplicadores) ou detailed. |
| [custo-folha-simulator](skills/custo-folha-simulator/) | Custo total empregador (salários + encargos + provisões). Estimate ou CSV roster. |
| [reajuste-impact-calculator](skills/reajuste-impact-calculator/) | Impacto financeiro de reajuste salarial (flat, por nível ou por área) com × 1,555 full load. |
| [stock-options-calculator](skills/stock-options-calculator/) | Modela vesting, diluição, cenários de exit em empresas de capital fechado. |

### Planejamento & estratégia (4)

| Skill | O que faz |
|---|---|
| [workforce-headcount-plan](skills/workforce-headcount-plan/) | Plano de headcount forward-looking amarrado a crescimento/receita: hires por função e trimestre, custo incremental, cenários Conservador/Base/Agressivo. |
| [hr-initiative-roi](skills/hr-initiative-roi/) | Business case de uma iniciativa de People (retenção, L&D, ramp): ROI, payback, net benefit em 3 anos, com sensibilidade. |
| [skills-gap-analysis](skills/skills-gap-analysis/) | Gap de capacidade: inventário de skills vs o que a estratégia exige → prioridade + decisão build/buy/borrow. |
| [people-strategy-okr-builder](skills/people-strategy-okr-builder/) | Constrói o plano estratégico de People: prioridades amarradas ao negócio + OKRs mensuráveis + roadmap trimestral. |

### Assessments HTML interativos (4)

| Skill | O que faz |
|---|---|
| [comp-level-simulator](skills/comp-level-simulator/) | Simulador interativo de nível de cargo usando metodologia de 4 pilares. |
| [hr-data-maturity-assessment](skills/hr-data-maturity-assessment/) | Assessment de maturidade de dados de RH (5 níveis × 5 dimensões). |
| [ai-native-hr](skills/ai-native-hr/) | Assessment de prontidão pra IA em RH baseado no [AI Maturity Map da Comp](https://comp.vc/ai-maturity-map?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=ai-maturity-map) (N1-N5 por área). |
| [org-design-assessment](skills/org-design-assessment/) | Maturidade de design organizacional (4 pilares × 3 perguntas, score 0-100). |

### Analyzers de dados (11)

| Skill | O que faz |
|---|---|
| [paygap-analysis-generator](skills/paygap-analysis-generator/) | Relatório de pay gap de gênero a partir de qualquer roster (CSV/XLSX). Confidencialidade ≥3 por gênero. |
| [comp-ratio-analyzer](skills/comp-ratio-analyzer/) | Compa-ratio do roster vs bandas salariais. Outliers + custo pra equalizar. |
| [promotion-equity-analyzer](skills/promotion-equity-analyzer/) | Equidade de promoções por gênero. Gap F vs M, disparidade por área. |
| [regretted-attrition-analyzer](skills/regretted-attrition-analyzer/) | Padrões em desligamentos regretted (gestor, área, tenure, performance). |
| [flight-risk-forecast](skills/flight-risk-forecast/) | Score preditivo e explicável de risco de saída por pessoa a partir de sinais do roster. Ferramenta de planejamento, não veredito. |
| [people-scorecard](skills/people-scorecard/) | Pacote executivo de KPIs de People (headcount, attrition, tenure, span, mobilidade, representação) a partir de roster + eventos. |
| [manager-effectiveness-scorecard](skills/manager-effectiveness-scorecard/) | Diagnóstico de qualidade por gestor cruzando span, attrition do time, engajamento e promoções. |
| [representation-dei-funnel](skills/representation-dei-funnel/) | Diversidade ao longo do ciclo (contratação → promoção → saída) por recorte. Confidencialidade ≥3. |
| [recruiting-funnel-analytics](skills/recruiting-funnel-analytics/) | Conversão do funil de recrutamento, time-to-fill, aceitação de oferta, efetividade por fonte, gargalos. |
| [engagement-deep-dive](skills/engagement-deep-dive/) | Segmentação de pesquisa de engajamento (eNPS) por área/tenure/manager/nível. |
| [span-of-control-diagnostic](skills/span-of-control-diagnostic/) | Diagnóstico Span of Intelligence (org chart → classificação). |

### Análise qualitativa (1)

| Skill | O que faz |
|---|---|
| [exit-survey-theme-analyzer](skills/exit-survey-theme-analyzer/) | Comentários abertos (exit, pesquisas) → temas, sentimento, citações anonimizadas e sinais de alerta. |

### Generators conversacionais (7)

| Skill | O que faz |
|---|---|
| [onboarding-kit-generator](skills/onboarding-kit-generator/) | Plano 30/60/90 + checklist IT + 1:1s + welcome email + buddy script. |
| [job-profile-builder](skills/job-profile-builder/) | Entrevista o hiring manager → JD completa + scorecard + roteiro de entrevistas. |
| [candidate-screening](skills/candidate-screening/) | Ranking de candidatos contra scorecard com justificativa por critério. |
| [decision-memo-generator](skills/decision-memo-generator/) | Memo estruturado (problema → opções → recomendação → ask). |
| [ceo-people-update-drafter](skills/ceo-people-update-drafter/) | Update CHRO → CEO em formato 1-pager. |
| [board-people-slide-builder](skills/board-people-slide-builder/) | Slide People & Culture pra board (HTML 16:9 printable). |
| [comp-budget-defense-pack](skills/comp-budget-defense-pack/) | Pacote pra defender comp/headcount budget ao CFO/CEO. |

### Research (1)

| Skill | O que faz |
|---|---|
| [research-digest](skills/research-digest/) | Digest rolling de 12 semanas de papers (Org Design, Workforce Planning, IA na força de trabalho) traduzido pra PT-BR. |

### Orchestrator (1)

| Skill | O que faz |
|---|---|
| [chro-chief-of-staff](skills/chro-chief-of-staff/) | Chief of Staff conversacional do CHRO. Contexto, pré-meeting briefs, drafts de comunicação, open loops tracker. Orquestra os outros 35 skills. |

### Design system (1)

| Skill | O que faz |
|---|---|
| [comp-html-guidelines](skills/comp-html-guidelines/) | Skill default que aplica um guia visual leve da Comp a todo HTML (relatórios, dashboards, assessments): paleta, tipografia, componentes e um CSS base. As demais skills a acionam automaticamente sempre que geram HTML, pra o resultado sair consistente e bem-acabado. |

## Dual-platform (Code + Cowork)

Os 37 skills funcionam tanto em **Claude Code** quanto em **Claude Cowork**:
- **Claude Code**: roda os scripts Python e gera relatórios HTML ricos, assessments interativos e processamento de CSV em lote.
- **Claude Cowork** (claude.ai): faz a mesma análise inline e entrega o resultado em markdown. Quando a ferramenta de artifact está disponível, também renderiza a versão visual em HTML.

A metodologia (fórmulas, scoring, regras de confidencialidade) é idêntica nos dois ambientes. Para datasets grandes (acima de 50 linhas) ou outputs interativos standalone, o Claude Code entrega mais fidelidade.

## Instalação só de um skill específico

Pra puxar só um (em vez do plugin inteiro), baixe o `.zip` da [release mais recente](https://github.com/trycomp-io/comp-skills/releases/latest) e descompacte em `~/.claude/skills/`.

## Privacidade

Esses skills rodam **localmente** no seu Claude. Dados de salário, rosters e qualquer análise ficam na sua máquina. Nada disso é enviado pra fora.

Na primeira execução (interativa), cada skill pergunta uma única vez se você quer:
1. **Atualizações por email** (opcional): se você informar um email, ele é registrado pra avisar quando um skill melhora. O registro envia email, nome do skill, versão e um identificador anônimo de instalação (`instance_id`). Deixe em branco pra pular. Se você rodar um skill diferente depois, esse registro é reenviado uma vez por skill (mesmo email + nome do novo skill); rode com email em branco pra não enviar.
2. **Telemetria de uso** (default: **off**). Se ativada, cada execução envia apenas: nome do skill, versão, `event_type`, o `instance_id` e um timestamp. **Não** inclui email, inputs, outputs nem dados de roster.

Quando a entrada vem por pipe (stdin não-interativo), nenhum prompt é exibido. As preferências ficam em `~/.comp-skills/config.json` (permissão `600`); apague o arquivo a qualquer momento pra revogar. As chamadas de rede só acontecem se houver uma API key configurada (`EAM_API_KEY`); o endpoint é `EAM_API_URL` (configurável).

Ambos os opt-ins ficam em `~/.comp-skills/config.json`. Apague o arquivo a qualquer momento para revogar.

## Issues e feedback

Abra uma [issue](https://github.com/trycomp-io/comp-skills/issues). Lemos todas.

## Licença

[MIT](LICENSE). Livre para usar, forkar e redistribuir. Atribuição é bem-vinda.

## Sobre a Comp

A Comp ajuda empresas em crescimento rápido a construir e operar um RH AI-native. Embarcamos executivos sêniores de RH e engenheiros de IA nos times dos nossos clientes. Esses skills são uma fatia pequena do que construímos internamente, liberada porque ferramenta de RH melhor é boa pra todo mundo.

[comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=mirror-readme-footer)
