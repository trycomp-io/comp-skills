# ai-native-hr

Skill gratuito do Claude para líderes de RH & People. Gera um assessment HTML interativo de prontidão para IA em RH, baseado no [AI Maturity Map da Comp](https://comp.vc/ai-maturity-map?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=ai-maturity-map).

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-ai-native-hr)).

## O que faz

Gera um HTML em ~3 segundos. CHRO/Head of People responde 15 perguntas em ~5 minutos. Output: nível N1-N5 por área de RH + alerta de dispersão entre áreas + próxima fronteira + armadilha frequente em cada transição.

Útil para:
- Diagnóstico claro de onde o RH está em IA hoje
- Roadmap defensável pra leadership team
- Identificar dispersão entre áreas (recrutamento avançou, comp ficou pra trás?)
- Evitar as armadilhas típicas de cada transição (ex: medir IA por tokens consumidos)

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

Instala o plugin `comp-skills` inteiro.

## Uso

Basta falar com o Claude. Exemplos:

- "Quero avaliar a maturidade de IA do meu RH"
- "Gera o assessment do AI Maturity Map pra mim"
- "Como está minha empresa em IA pra RH?"
- "Diagnóstico de prontidão pra IA: RH"

## Framework

### 5 Níveis (do AI Maturity Map da Comp)
- **N1** Produtividade Individual
- **N2** Produtividade do Time
- **N3** Sistema Operacional Contextual
- **N4** Inteligência de Decisão
- **N5** Inteligência Adaptativa

### 5 Áreas de RH avaliadas
1. Recrutamento & TA
2. Compensação & Rewards
3. L&D / Performance
4. People Ops / Admin
5. People Analytics / Decisão

3 perguntas por área = 15 perguntas no total.

## Output

- **Nível geral** (mediana das áreas, alinhado com "area-based progression" do framework)
- **Nível por área** (heatmap)
- **Alerta de dispersão** se diferença de 2+ níveis entre áreas
- **Próxima fronteira** por área (o que faz mover N → N+1)
- **Armadilha frequente** por área (erros típicos de cada transição)

## O que é compartilhado com a Comp

Na primeira execução você será perguntado sobre:
1. Seu email (opcional), usado apenas para notificar atualizações do skill.
2. Telemetria anônima (default: off): se ativada, envia nome do skill, versão, um identificador anônimo de instalação e um timestamp por execução. **Nunca envia respostas, scores ou o HTML que você gera.**

O HTML em si **nunca** chama o servidor. É JS puro client-side.

## Issues

Abra uma issue em [trycomp-io/comp-skills](https://github.com/trycomp-io/comp-skills/issues) com a label `eam`.

Powered by Comp · Free skills for HR & People leaders.
