# research-digest

Skill gratuito do Claude para líderes de RH & People. Cura um digest rolling de 12 semanas de papers e publicações de alto sinal sobre **Org Design**, **Workforce Planning** e **impacto da IA na força de trabalho**, traduzido pra PT-BR com sumários executivos e key takeaways. Output HTML único, auto-contido, compartilhe via Drive/email/hosting estático.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-research-digest)).

## O que faz

Cada vez que você roda:
1. Puxa as últimas 12 semanas de papers/reports de fontes acadêmicas (OpenAlex, arXiv) e de prática (consultorias + thought leaders)
2. Traduz títulos, abstracts e key takeaways pra PT-BR
3. Renderiza um digest HTML executivo agrupado por tema

Feito para líderes de RH/People que querem ficar na fronteira sem se afogar em literatura.

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

Instala o plugin `comp-skills` inteiro (4 skills, um dos quais é este).

## Uso

Basta falar com o Claude. Exemplos:

- "Gera meu radar de papers dessa janela"
- "Quero ver as novidades em org design das últimas semanas"
- "Atualização de pesquisa sobre IA no trabalho"
- "Research review pra eu mandar pro CEO"

O Claude orquestra os 3 passos (fetch → traduz → renderiza) e devolve um `research-digest-YYYY-MM-DD.html` no diretório atual.

## Agendamento (power users)

O skill é on-demand por default. Para rodar em cadência, agende via:

**Claude Code** (se você usa):
```
/schedule weekly "rode meu research-digest"
```

**Unix cron** (manual):
```cron
0 9 * * MON cd ~/projects/my-research && claude "rode o research-digest"
```

Cadência sweet spot: **mensal** (combina com a janela rolling de 12 semanas, material novo garantido).

## O que é compartilhado com a Comp

Na primeira execução você será perguntado sobre:
1. Seu email (opcional): usado apenas para notificar atualizações do skill.
2. Telemetria anônima (default: off): se ativada, envia nome do skill, versão, um identificador anônimo de instalação e um timestamp por execução. **Nunca envia o conteúdo do digest, as fontes nem seus inputs.**

O HTML de saída fica 100% na sua máquina. O skill busca de APIs públicas de pesquisa (OpenAlex, arXiv), sem credenciais, sem tracking.

Ambos os opt-ins ficam em `~/.comp-skills/config.json` localmente. Edite ou apague o arquivo a qualquer momento para revogar.

## Cobertura de fontes

- **Acadêmico**: OpenAlex, arXiv (funciona através do OpenAlex)
- **Prática**: top consultorias (McKinsey, BCG, Bain, Deloitte, Mercer, WTW, Korn Ferry) + thought leaders (Josh Bersin, Galloway, etc.) via RSS

Catálogo completo: `references/sources.md`.

## Issues

Abra uma issue em [trycomp-io/comp-skills](https://github.com/trycomp-io/comp-skills/issues) com a label `eam`.

Powered by Comp · Free skills for HR & People leaders.
