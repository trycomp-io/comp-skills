# Span of Intelligence: Metodologia

Baseada no artigo ["De Span of Control a Span of Intelligence"](https://cajuina.org/principais/coluna-comp/de-span-of-control-a-span-of-intelligence/) da coluna Comp na Cajuína.

## Mudança de paradigma

**Span of Control tradicional**: número fixo de diretos por gestor (geralmente 6-10). Assume que todos os subordinados são humanos consumindo capacidade similar de gestão.

**Span of Intelligence**: planeja a *inteligência* do trabalho, não a *força* de trabalho. Reconhece que:
- 1 humano ≠ 1 unidade de capacidade gerencial
- IA executa parte do trabalho transacional
- Gestores viram orquestradores (humanos + agentes)
- Estruturas tendem a achatar e se senior-izar conforme IA absorve operacional

> "E se o futuro for menos sobre planejar a força de trabalho e mais sobre planejar a inteligência do trabalho?"

## 12 critérios qualitativos (síntese do artigo + literatura)

O artigo propõe avaliação por 12 critérios qualitativos em vez de um número ideal único. Sintetizamos como:

1. **Complexidade do trabalho**: transacional vs estratégico
2. **Padronização do processo**: repetível vs ad-hoc
3. **Acoplamento entre membros**: independente vs interdependente
4. **Expertise técnica do líder**: domínio profundo vs superficial
5. **Tempo do líder no papel**: curva de experiência
6. **Senioridade média dos diretos**: sêniores precisam menos coaching
7. **Quantidade de agentes IA no time**: agentes extendem capacidade
8. **% do trabalho já automatizado**: quanto IA absorve
9. **Autonomia delegada**: decisões descentralizadas vs centralizadas
10. **Distribuição geográfica**: local vs distribuído
11. **Tipo de papel**: IC manager vs people manager puro
12. **Métrica de output**: inteligência gerada vs horas trabalhadas

## Como o skill operacionaliza

O CSV de input pode incluir colunas extras opcionais que ajustam a análise:
- `ai_agents`: número de agentes IA dedicados a esse gestor/time
- `automation_pct`: % do trabalho do time já automatizado (0-100)
- `complexity`: low / medium / high

Quando essas colunas estão presentes, o skill calcula:
- **Span tradicional** = nº de diretos humanos
- **Span ajustado** = diretos × (1 - automation_pct/100)
- **Classificação SoI**:
  - **Tradicional**: nenhum agente, automation <20%, span normal
  - **Híbrido**: 1+ agente OU automation 20-60%
  - **Orquestração**: 2+ agentes OU automation 60%+
  - **Subutilizado**: span <4 sem automação significativa (oportunidade de senior-izar)

## Recomendações

Em vez de "quebre se >15 diretos", o skill agora sugere:
- Se span >12 e automation <30%: **avalie agentes** antes de splitting
- Se span <4 e automation alta: **promova gestor a IC sênior** (estrutura achatando)
- Se complexity=high e zero agentes: **identifique tarefas transacionais pra automação** (libera bandwidth do gestor)

## Limitação assumida

O artigo enfatiza avaliação qualitativa, e o skill só consegue capturar o que estiver no CSV. CHRO precisa enriquecer dados pra extrair valor máximo. O skill identifica essa lacuna no output ("dados de IA não fornecidos, adicione coluna `ai_agents` pra análise completa").
