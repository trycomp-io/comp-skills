# span-of-control-diagnostic

Skill gratuito do Claude para líderes de RH & People. Diagnóstico de **Span of Intelligence**, evolução do span of control tradicional, baseado no artigo [De Span of Control a Span of Intelligence](https://cajuina.org/principais/coluna-comp/de-span-of-control-a-span-of-intelligence/) da coluna Comp na Cajuína.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-span-of-control-diagnostic)).

## O que faz

Lê o org chart (CSV/XLSX) e gera relatório HTML com classificação dos gestores em 5 categorias (Tradicional / Híbrido / Orquestração / Subutilizado / Sobrecarregado-sem-IA), recomendações específicas e estatísticas por área.

Diferente de diagnósticos clássicos que dizem "quebre se >15 diretos", esse skill reframe pra "automatize ou senior-ize", alinhado com a tese de que estruturas tendem a achatar quando IA absorve transacional.

Útil para:
- Avaliar oportunidades de senior-ização da org
- Identificar onde adicionar agentes IA antes de splitting de times
- Mapear camadas excessivas
- Defender reorgs com framework defensável

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Roda um diagnóstico do meu org chart"
"Análise de span of control nessa planilha"
"Span of intelligence: quanto IA tem no time"
```

## Colunas do CSV

Mínimo: `employee_id`, `name`, `manager_id`. Auto-detect funciona em PT/EN (`matricula`, `gestor`, `reports_to`, etc.).

Pra análise completa Span of Intelligence, adicione:
- `ai_agents`: nº de agentes IA no time
- `automation_pct`: % trabalho automatizado (0-100)
- `complexity`: low/medium/high

## Classificação SoI

| Categoria | Critério | Recomendação |
|---|---|---|
| Tradicional | Span normal, zero IA | OK pra trabalho transacional clássico |
| Híbrido | 1+ agente ou 20-60% auto | Continue agentificando |
| Orquestração | 2+ agentes ou 60%+ auto | Mensure inteligência, não horas |
| Subutilizado | Span <4 sem IA | Senior-ize, elimine camada |
| Sobrecarregado (sem IA) | Span >12 sem IA | Avalie agentes antes de splitting |

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia dados do org chart.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
