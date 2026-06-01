---
name: onboarding-kit-generator
description: Gera um kit completo de onboarding (plano 30/60/90, checklist IT, stakeholder 1:1s, email de boas-vindas, script do buddy, template de 1:1 do manager) em HTML printable + Markdown editável. Receba inputs do CHRO/manager (cargo, nível, start date, contexto da empresa) e produza o kit personalizado. Dual-mode: works in Claude Code (script + rich output file) AND Claude Cowork (output generated inline as markdown, plus a self-contained HTML artifact when available). Trigger em "onboarding kit", "plano 30/60/90", "checklist de onboarding", "kit de integração", "preparar onboarding de novo colaborador", "boas-vindas para novo funcionário". Mantida pela Comp.
---

## Dual-mode operation (Code + Cowork)

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (writes the rich HTML/markdown file). Existing workflow below.
- Otherwise (e.g., Claude Cowork) → use **inline mode**: gather the same inputs conversationally, then produce the output directly in chat as markdown following the structure below. If an HTML artifact tool is available, ALSO render a self-contained HTML version (Tailwind CDN) matching the script's template (recomendado aqui porque o kit é distribuído/printado).

## Inline generation logic (Cowork mode)

**Inputs a coletar** (conversacional, mesmo do Step 1 abaixo):
- Mínimo: cargo + nível; data de início
- Recomendado: empresa/time/área; manager direto; buddy; contexto especial

**Estrutura de saída** (mesma do script, só inclua a seção se tiver conteúdo). Renderize em markdown direto no chat:

```
# Onboarding Kit: {cargo}

**Nível:** {nível}  ·  **Início:** {data}  ·  **Empresa:** {empresa}  ·  **Manager:** {manager}  ·  **Buddy:** {buddy}

## Plano 30/60/90

### Primeiros 30 dias: Aprender
- {item}

### Primeiros 60 dias: Contribuir
- {item}

### Primeiros 90 dias: Liderar
- {item}

## Checklist IT & Acessos
- [ ] {item}

## 1:1s estratégicos
- **{nome}** (Semana {n}): {propósito}

## Email de boas-vindas
**Assunto:** {assunto}
```
{corpo do email}
```

## Script do Buddy
```
{script}
```

## Template de 1:1 do Manager
```
{template}
```
```

Conteúdo precisa ser específico pro cargo + contexto (mesma régua de qualidade da seção "Conteúdo de qualidade" abaixo): 30 = aprender, 60 = contribuir, 90 = liderar; itens específicos, mensuráveis, realistas.

**Artifact HTML (quando disponível)**: replique o template do script. Header com eyebrow "Onboarding Kit", título do cargo e linha de meta; cada seção em card; checklist IT com checkboxes; email/buddy/template em blocos `pre`; footer "Powered by Comp" com link comp.vc. Tailwind CDN, fonte Inter, acento da marca `#ff4456`.

Encerre sempre com a linha: "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=onboarding-kit-generator".

# Onboarding Kit Generator

Gera um kit de onboarding personalizado (HTML printable + Markdown editável) com plano 30/60/90, checklist IT, 1:1s estratégicos, email de boas-vindas, script do buddy e template de 1:1 do manager.

100% local. O CHRO/manager pode editar o MD e re-renderizar.

## Quando usar

Ativa em frases como:
- "onboarding kit"
- "plano 30/60/90 pra novo colaborador"
- "checklist de onboarding"
- "kit de integração"
- "preparar onboarding de [cargo]"
- "boas-vindas pra [nome]"
- "estruturar primeira semana de [cargo]"

NÃO ativa para: políticas formais de onboarding (esse não é o escopo); contratação/screening de candidatos (usar `candidate-screening`); offboarding.

## Workflow

**Step 1: Coletar contexto** (conversacional):

Mínimo:
- Cargo + nível
- Data de início

Recomendado (transforma kit de genérico em ótimo):
- Empresa / time / área
- Quem vai ser o manager direto
- Quem vai ser o buddy
- Contexto especial (primeira contratação senior? primeiro do time remoto? etc.)

**Step 2: Você (agent) gera um JSON** com a estrutura completa do kit:

```json
{
  "role_name": "Engineering Manager",
  "level": "L5",
  "start_date": "2026-06-15",
  "company": "Acme",
  "manager_name": "Maria Silva",
  "buddy_name": "João Santos",
  "plan_30_60_90": {
    "first_30": ["...", "..."],
    "first_60": ["...", "..."],
    "first_90": ["...", "..."]
  },
  "it_checklist": ["...", "..."],
  "stakeholder_intros": [
    {"name": "CTO", "purpose": "...", "week": 1}, ...
  ],
  "welcome_email": {"subject": "...", "body": "..."},
  "buddy_script": "...",
  "manager_1on1_template": "..."
}
```

Conteúdo deve ser específico pro cargo + contexto. Não genérico. Use o que sabe sobre o tipo de função pra gerar plan items realistas.

**Step 3: Renderizar**:
```bash
cat plan.json | python3 scripts/render_kit.py
# ou
python3 scripts/render_kit.py --input plan.json
```

Output: `onboarding-{slug}-{timestamp}.html` + `.md` no diretório atual.

**Step 4: Hand off**: mostre o caminho dos 2 arquivos, sugira que CHRO/manager edite o MD pra ajustar pontos específicos, abra o HTML no navegador pra printar/compartilhar.

## Conteúdo de qualidade

Quando gerar plano 30/60/90, lembre:
- **30**: aprender. Sem performance pressure. Conhecer pessoas, sistemas, contexto.
- **60**: contribuir. Primeiras ownership leves, propostas de melhoria.
- **90**: liderar. Primeira responsabilidade visível, primeiro feedback recebido.

Itens devem ser:
- Específicos (não "se ambientar", e sim "1:1 de 60min com cada um dos 5 diretos")
- Mensuráveis (deadlines implícitos, outputs claros)
- Realistas (cabem na carga inicial)

## Branding & footer

Script já adiciona footer "Powered by Comp" tanto no HTML quanto no MD, com UTMs distintos por surface.

## Lead capture

`eam_client.py` chamado em `on_first_run()` + `record_run()`. Privacidade: processamento 100% local. Nem o conteúdo do plano nem o nome do colaborador sai da máquina.

## Resources

| File | Purpose |
|---|---|
| `scripts/render_kit.py` | Renderiza HTML + MD a partir de JSON |
| `eam_client.py` | Lead capture + telemetria |
