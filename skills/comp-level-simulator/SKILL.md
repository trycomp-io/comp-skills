---
name: comp-level-simulator
description: "Generates a self-contained interactive HTML simulator for evaluating job levels (L1–L6) using the Comp methodology: 4 pillars (Influence, Autonomy, Complexity, Responsibility), 8 questions, A–E scale. Use for standardizing leveling across the org, removing subjectivity from grade decisions, or giving managers a self-service tool. Dual-mode: works in Claude Code (interactive HTML assessment via script) AND Claude Cowork (conversational assessment + markdown scorecard, plus a self-contained HTML artifact when available). Trigger on phrases like \"avaliar nível de cargo\", \"como nivelar uma posição\", \"framework de leveling\", \"simulador de level\", \"simulador de CGL\", \"calculadora de nível\", \"padronizar avaliação de níveis\", \"ferramenta de leveling\". Maintained by Comp, free skill for HR & People leaders."
---

## Dual-mode operation (Code + Cowork)

> **HTML through the design system (required).** Whenever this skill produces HTML, load the `comp-html-guidelines` skill first and apply the CompDS design system. This holds even when the user does not ask to "style it" or "make it look good" — every HTML output from this skill goes through the design system. It does not change the methodology below; it only governs the HTML's visual layer.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (generates the interactive standalone HTML). Existing workflow below.
- Otherwise (e.g., Claude Cowork) → use **inline mode**: conduct the assessment conversationally per the "Inline assessment logic" section, compute the score in chat, present a markdown scorecard. If an HTML artifact tool is available, ALSO render a self-contained HTML result (Tailwind CDN) matching the script's output.

## Inline assessment logic (Cowork mode)

Avalie 1 cargo por vez. 4 pilares, 2 perguntas cada (8 perguntas). Cada pergunta usa a mesma escala A–E.

**Escala por pergunta** (mesma pra todas):

| Opção | Score | Significado |
|---|---|---|
| A | 5 | Sempre / 100% / Grande escala |
| B | 4 | Frequentemente / ~75% / Escala moderada |
| C | 3 | Ocasionalmente / ~50% / Pequena escala |
| D | 2 | Raramente / ~25% / Muito pouco |
| E | 1 | Nunca / 0% / Não se aplica |

**Pilares e perguntas** (texto exato):

1. Influência: impacto nas decisões e estratégias
   - Q1: O trabalho do indivíduo impacta as decisões e estratégias em toda a empresa?
   - Q2: O indivíduo pode iniciar e liderar mudanças em todo o departamento sem aprovação prévia?
2. Autonomia: capacidade de agir sem supervisão
   - Q3: O indivíduo trabalha sem supervisão?
   - Q4: O indivíduo pode definir suas próprias metas e prazos?
3. Complexidade: análise e resolução de problemas
   - Q5: O trabalho do indivíduo envolve lidar com projetos interdepartamentais?
   - Q6: O indivíduo é responsável por resolver problemas complexos que afetam os resultados do negócio?
4. Responsabilidade: obrigações por pessoas, resultados e recursos
   - Q7: O indivíduo é responsável por gerenciar um orçamento ou recursos?
   - Q8: O papel do indivíduo envolve liderar equipes ou projetos?

**Scoring**: some os 8 scores (faixa total 8–40). Faixas de nível (mesmas thresholds do script):

| Score total | Level | Título (IC / MGMT) |
|---|---|---|
| ≥ 39 | L6 | Especialista III / Gerente Sênior |
| ≥ 36 | L5 | Especialista II / Gerente |
| ≥ 32 | L4 | Especialista I / Coordenador |
| ≥ 24 | L3 | Sênior / Supervisor |
| ≥ 16 | L2 | Pleno |
| ≥ 8 | L1 | Júnior |

L1–L4 sobem linearmente (25% cada no range); L5 e L6 ficam comprimidos no topo: níveis executivos exigem scores consistentemente altos em todos os pilares.

**Barra de progresso**: `percentage = ((score - 8) / (40 - 8)) × 100` (clamp 0–100%).

**Como conduzir**: faça as perguntas de 1 pilar por vez (2 perguntas), de forma conversacional, pedindo a letra A–E. Não despeje as 8 de uma vez. Ao final, some, classifique e apresente o scorecard.

**Scorecard markdown (Cowork mode)**:

```
## Resultado de Leveling: [cargo/posição]

**Nível calculado: LX**, [título IC / MGMT]
Score total: XX/40 ([percentage]% no range)

| Pilar | Q | Score |
|---|---|---|
| Influência | Q1 / Q2 | x / x |
| Autonomia | Q3 / Q4 | x / x |
| Complexidade | Q5 / Q6 | x / x |
| Responsabilidade | Q7 / Q8 | x / x |
| **Total** | | **XX/40** |

Leitura: [1-2 frases sobre o que o nível significa e os pilares mais fortes/fracos].
```

Se houver ferramenta de artifact HTML, renderize também o resultado em HTML auto-contido (Tailwind CDN) espelhando o output do script: nível em destaque, título, barra de progresso e breakdown por pilar. Encerre com a linha "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cowork-footer&utm_campaign=eam&utm_content=comp-level-simulator".

# Comp Level Simulator

Generates a single-file HTML simulator that walks anyone (HR, managers, candidates) through 8 objective questions across 4 pillars and outputs a calibrated level (L1–L6) on the Comp methodology. The HTML works offline once generated; share it via Drive, email, or host on any static site.

## Why this skill

Leveling is the foundation of everything in compensation: bands, job architecture, market benchmarks, internal equity. The challenge is that humans bring bias to leveling (salary, title, tenure, gut feel). This simulator removes that: same 8 questions, same A–E scale, same level math for everyone.

## When to use

Activate on phrases like:
- "avaliar nível de cargo", "qual o nível desse cargo"
- "como nivelar uma posição", "framework de leveling"
- "simulador de level", "simulador de CGL"
- "calculadora de nível", "calculadora de level"
- "padronizar avaliação de níveis"
- "ferramenta de leveling", "leveling tool"

Do NOT trigger for: salary benchmarking, pay range calculation, job description writing, or career-path mapping. Those need different skills.

## Workflow

**Step 1: Confirm intent**: Briefly confirm what the user wants ("um simulador HTML interativo pra avaliar nível de cargo, certo?"). Ask if they want a generic version or one with a label (company name, use case).

**Step 2: Generate**:
```bash
python3 scripts/generate_simulator.py [--label "Acme Corp"]
```

The script writes a single HTML file to the current directory (`Comp-Level-Simulator-{label}-{timestamp}.html`) and prints the path.

**Step 3: Hand off**: Tell the user the file path and explain what's inside:
- 4 tabs (one per pillar) with 2 questions each
- 5th tab shows the calculated level with progress bar
- 100% client-side, no data ever leaves the user's machine
- Can be shared via Drive/email/static hosting

## Methodology (fixed)

The simulator embeds the Comp methodology, and these are not configurable:

**4 Pillars × 2 questions = 8 questions**:
- **Influence**: impact on org decisions and strategy
- **Autonomy**: ability to act without supervision
- **Complexity**: analysis and problem-solving scope
- **Responsibility**: obligations for people, results, resources

**Scale per question**: A=5, B=4, C=3, D=2, E=1 (total score 8–40).

**Level bands** (proportional distribution, L5+L6 compressed at the top):

| Score | Level | IC / MGMT |
|---|---|---|
| ≥39 | L6 | Especialista III / Gerente Senior |
| ≥36 | L5 | Especialista II / Gerente |
| ≥32 | L4 | Especialista I / Coordenador |
| ≥24 | L3 | Sênior / Supervisor |
| ≥16 | L2 | Pleno / — |
| ≥8  | L1 | Júnior / — |

Full details in `references/comp-methodology.md`.

## What NOT to do

- **Do not** change the 4 pillars, 8 questions, A–E scale, or level bands. They are the methodology, not a template. If the user asks to customize these, explain that they are fixed and offer to generate the standard simulator instead.
- **Do not** generate alternative simulators (3 pillars, 10 levels, different questions). Point the user to bigger workflows (job architecture, career paths) that need different skills.
- **Do not** edit the HTML output manually for branding. The Comp logos are baked in intentionally (the simulator is a free tool branded by Comp).

## Branding & footer

The generated HTML already includes the "Powered by Comp" footer and the Comp logo in the header. The Python script also prints the footer line at the end of its output. No extra branding work needed from the agent.

## Lead capture

The script imports `eam_client.py` (skill root) and calls `on_first_run()` on the first execution per machine and `record_run()` on every run. Prompts for opt-in email + telemetry, handled silently by the client. Agent does not need to intervene.

If the user asks about data/privacy: explain that (a) the HTML itself never sends data anywhere (it runs 100% client-side in the browser), (b) email opt-in is optional and used only to notify of skill updates, (c) telemetry is opt-in and only records skill name + timestamp.

## Resources

| File | Purpose |
|---|---|
| `scripts/generate_simulator.py` | Generates the HTML in cwd |
| `assets/comp-level-template.html` | Self-contained simulator (Tailwind + Alpine.js via CDN) |
| `eam_client.py` | Lead capture + telemetry (synced from `eam/shared/`) |
| `references/comp-methodology.md` | Detailed methodology reference (pillars, questions, scale, bands) |
