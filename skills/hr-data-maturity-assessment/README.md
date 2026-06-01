# hr-data-maturity-assessment

Skill gratuito do Claude para líderes de RH & People. Gera um assessment HTML interativo que avalia a maturidade de dados do RH em 5 dimensões × 5 níveis.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-hr-data-maturity-assessment)).

## O que faz

Gera um arquivo HTML em ~3 segundos. CHRO/Head of People responde 15 perguntas em ~5 minutos. Output: nível 1-5 por dimensão + nível geral + roadmap personalizado pra avançar ao próximo nível em cada dimensão.

Útil para:
- Diagnóstico inicial antes de planejar investimentos em people analytics
- Alinhar leadership team sobre onde o RH está hoje em dados
- Roadmap defensável pra propor pro CFO/CEO
- Benchmark antes/depois de iniciativas de modernização

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

Instala o plugin `comp-skills` inteiro.

## Uso

Basta falar com o Claude. Exemplos:

- "Gera um assessment de maturidade de dados pra eu rodar com meu time de RH"
- "Diagnóstico de people analytics na minha empresa"
- "Qual o nível do nosso RH em dados? Tem como avaliar?"
- "Roadmap pra evoluir o RH em dados, me ajuda a estruturar"

## Framework

### 5 Níveis
1. **Ad-hoc**: RH em planilhas, dados fragmentados
2. **Operacional**: HRIS centralizado, reporting sob demanda
3. **Reporting**: Dashboards com cadência, métricas core monitoradas
4. **Analytics**: Análises causa-raiz, segmentação, predição básica
5. **AI-native**: Agentes assistentes, predição contínua, automação

### 5 Dimensões
1. **Coleta & Integração**
2. **Qualidade & Governança**
3. **Reporting & Métricas**
4. **Análise & Decisão**
5. **Tech & AI**

3 perguntas por dimensão = 15 perguntas no total.

## O que é compartilhado com a Comp

Na primeira execução você será perguntado sobre:
1. Seu email (opcional), usado apenas para notificar atualizações do skill.
2. Telemetria anônima (default: off): se ativada, envia nome do skill, versão, um identificador anônimo de instalação e um timestamp por execução. **Nunca envia respostas, scores ou o HTML que você gera.**

O HTML em si **nunca** chama o servidor. É JS puro client-side. Tudo que você responde fica no navegador.

## Issues

Abra uma issue em [trycomp-io/comp-skills](https://github.com/trycomp-io/comp-skills/issues) com a label `eam`.

Powered by Comp · Free skills for HR & People leaders.
