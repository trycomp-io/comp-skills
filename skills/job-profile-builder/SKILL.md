---
name: job-profile-builder
description: Conduz uma entrevista estruturada com o hiring manager (10-15 perguntas) e gera um Job Profile completo: Resumo executivo (por que agora, outcomes, deal-breakers), JD (sobre a vaga, responsabilidades, requisitos, nice-to-have, oferta), Scorecard de avaliação ponderado, e Roteiro de Entrevistas com perguntas por estágio e o que procurar. Output em HTML printable + Markdown editável. Dual-mode: works in Claude Code (script + rich output file) AND Claude Cowork (output generated inline as markdown, plus a self-contained HTML artifact when available). Trigger em "criar JD", "job description", "perfil da vaga", "abrir vaga de [cargo]", "entrevistar hiring manager", "job profile", "scorecard de entrevista". Mantida pela Comp.
---

## Dual-mode operation (Code + Cowork)

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (writes the rich HTML/markdown file). Existing workflow below.
- Otherwise (e.g., Claude Cowork) → use **inline mode**: gather the same inputs conversationally, then produce the output directly in chat as markdown following the structure below. If an HTML artifact tool is available, ALSO render a self-contained HTML version (Tailwind CDN) matching the script's template.

## Inline generation logic (Cowork mode)

**Inputs a coletar**: conduza a mesma entrevista estruturada em blocos do Step 1 abaixo (contexto da posição, outcomes esperados, filtros/diferenciais, processo). Não pergunte tudo de uma vez.

**Estrutura de saída** (mesma do script, só inclua a seção se tiver conteúdo). Renderize em markdown direto no chat:

```
# Job Profile: {cargo}

**Nível:** {nível}  ·  **Área:** {área}  ·  **Empresa:** {empresa}  ·  **Hiring Manager:** {manager}

## Resumo executivo
**Por que agora:** {why_now}

**Outcomes em 6 meses:**
- {outcome}

**Deal-breakers:**
- {deal_breaker}

## Job Description
{about_role}

### Responsabilidades
- {item}
### Requisitos
- {item}
### Diferenciais
- {item}
### O que oferecemos
- {item}

## Scorecard
| Critério | Peso | Rubrica |
|---|---|---|
| {critério} | {1-5} | 5=...; 3=...; 1=... |

## Roteiro de entrevistas
- **{estágio}**: {pergunta}
  - *O que procurar:* {what_to_look_for}
```

Conteúdo deve ser específico ao que o hiring manager expressou (mesma régua de qualidade da seção "Qualidade do output" abaixo): JD que vende a vaga, responsabilidades acionáveis, scorecard com 5-8 critérios e rubrica concreta, perguntas behavioural (STAR).

**Artifact HTML (quando disponível)**: replique o template do script. Header com eyebrow "Job Profile", título do cargo e meta; cards de Resumo executivo, Job Description, Scorecard (linha por critério com pill de peso) e Roteiro de entrevistas (pill de estágio por pergunta); footer "Powered by Comp". Tailwind CDN, fonte Inter, acento `#ff4456`.

Encerre sempre com: "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=job-profile-builder".

# Job Profile Builder

Skill conversacional que entrevista o hiring manager e produz um pacote completo de abertura de vaga: JD + scorecard + roteiro de entrevistas.

## Quando usar

Ativa em frases como:
- "criar JD", "job description"
- "perfil da vaga"
- "abrir vaga de [cargo]"
- "entrevistar hiring manager"
- "job profile / scorecard de entrevista"
- "ajuda a estruturar uma posição"

NÃO ativa para: triagem de candidatos (usar `candidate-screening`); calibração de salário (usar `pj-vs-clt-calculator` ou skills de comp); onboarding de hire (usar `onboarding-kit-generator`).

## Workflow

**Step 1: Entrevista estruturada com o hiring manager** (você conduz a conversa):

Não pergunte tudo de uma vez. Faça em blocos:

**Bloco 1: Contexto da posição (5 perguntas)**
1. Qual a posição e o nível? (cargo + L1-L8 ou equivalente)
2. Por que essa vaga agora? (substituição, crescimento, nova capability)
3. A quem vai reportar e quem vai trabalhar com?
4. Em que área/time fica?
5. Modalidade (remoto, hybrid, presencial) e localização preferida?

**Bloco 2: Outcomes esperados (3-4 perguntas)**
6. O que essa pessoa precisa entregar nos primeiros 6 meses pra ser considerada um hire bem-sucedido?
7. O que essa pessoa precisa SABER (hard skills) pra entregar isso?
8. O que essa pessoa precisa SER (soft skills, comportamentos) pra entregar isso?

**Bloco 3: Filtros e diferenciais (3 perguntas)**
9. Deal-breakers (3-5 itens que automaticamente desqualificam)?
10. Diferenciais que seriam bônus (nice to have)?
11. Quem seria o candidato ideal? Algum perfil/empresa específica que vem na cabeça?

**Bloco 4: Processo (2-3 perguntas)**
12. Quais estágios de entrevista vão existir?
13. Quem entrevista em cada estágio?
14. Quanto tempo tem pra contratar (urgência)?

**Step 2: Gerar o JSON estruturado**:

```json
{
  "role_name": "Engineering Manager",
  "level": "L5",
  "area": "Engineering",
  "company": "Acme",
  "manager": "Maria Silva",
  "summary": {
    "why_now": "...",
    "key_outcomes_6_months": ["...", "..."],
    "deal_breakers": ["...", "..."]
  },
  "jd": {
    "about_role": "...",
    "responsibilities": ["...", "..."],
    "requirements": ["...", "..."],
    "nice_to_have": ["...", "..."],
    "what_we_offer": ["...", "..."]
  },
  "scorecard": [
    {"criterion": "Liderança técnica", "weight": 5, "rubric": "5=lidera arquiteturas críticas; 3=lidera projetos; 1=executa direção dos outros"}, ...
  ],
  "interview_questions": [
    {"stage": "Recruiter screen", "question": "...", "what_to_look_for": "..."}, ...
  ]
}
```

Conteúdo deve ser ESPECÍFICO ao contexto da entrevista. Não use boilerplate. Use as palavras e prioridades que o hiring manager expressou.

**Step 3: Renderizar**:
```bash
cat profile.json | python3 scripts/render_jd.py
```

Output: `jd-{slug}-{timestamp}.html` + `.md` no cwd.

**Step 4: Hand off**:
- HTML pra recruiter usar (printable, share via Drive)
- MD editável (ajustar tom, customizar pra plataforma)
- Sugira o que recruiter deve adaptar (parts mais sensíveis: salary range, benefícios específicos)

## Qualidade do output

Boa JD tem:
- **About role** que vende a posição (não só lista requisitos)
- **Responsabilidades** acionáveis (verbos no infinitivo, output mensurável)
- **Requisitos** separados de nice-to-have (rigor)
- **What we offer** específico (não "great culture", e sim "stock options + L5 banda salarial + 30 dias férias")

Bom scorecard tem:
- 5-8 critérios (não 15)
- Pesos que somam claramente (1-5 cada)
- Rubrica concreta (5 = ..., 3 = ..., 1 = ...), não "boa liderança"

Bom roteiro de entrevistas tem:
- Perguntas behavioural (STAR), não hipotéticas
- "What to look for" pra cada, calibra o entrevistador

## Branding & footer

Script adiciona footer "Powered by Comp" no HTML e MD com UTMs.

## Lead capture

`eam_client.py` chamado em `on_first_run()` + `record_run()`. Privacidade: 100% local.

## Resources

| File | Purpose |
|---|---|
| `scripts/render_jd.py` | Renderiza HTML + MD a partir de JSON |
| `eam_client.py` | Lead capture + telemetria |
