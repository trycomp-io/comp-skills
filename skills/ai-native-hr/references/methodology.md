# AI Native HR: Metodologia

Baseada no [AI Maturity Map](https://comp.vc/ai-maturity-map?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=ai-maturity-map) da Comp, adaptada pro contexto específico de RH.

## Os 5 Níveis (do framework Comp, traduzidos)

| Nível | Nome | Definição | Sinal característico | Limitação | Armadilha frequente |
|---|---|---|---|---|---|
| **N1** | **Produtividade Individual** | Pessoas usam IA pra ganhar produtividade no próprio trabalho. | Variância grande entre quem usa bem e quem não usa. | Ganhos concentrados em power users. | Medir sucesso por "uso de IA" (tokens, queries). |
| **N2** | **Produtividade do Time** | Skills e agentes compartilhados cobrem a maior parte das tarefas operacionais. | "Quase toda tarefa tem uma solução em IA, geralmente criada por outra pessoa." | Contexto ainda depende de humano. Cada solução opera isolada. | Medir por volume de skills/agentes criados. |
| **N3** | **Sistema Operacional Contextual** | Uma camada agêntica única executa trabalho complexo dentro de parâmetros humanos. | Uma pessoa empoderada toca a operação inteira do departamento via IA. | Definição de problema e abordagem ainda dependem de humano. | Tratar fontes de dados diferentes (estruturadas/não-estruturadas) como iguais. |
| **N4** | **Inteligência de Decisão** | Camada agêntica propõe decisões baseada nos padrões de julgamento dos melhores humanos. | Variância de qualidade de decisão desaparece, todas convergem pro melhor. | Sistema depende de feedback dos humanos com melhor julgamento. | Tratar todo feedback humano como igual, independente da qualidade do julgamento. |
| **N5** | **Inteligência Adaptativa** | Camada agêntica aprende sozinha dos resultados das decisões, refinando julgamento continuamente. | Resultados do departamento melhoram mês a mês sem intervenção humana específica. | Pouco validado empiricamente em escala. | — |

## Adaptação pra RH: Avaliação por Área

Conforme recomendação do artigo ("Different departments achieve different maturity levels simultaneously"), avaliamos 5 áreas de RH separadamente:

1. **Recrutamento & Talent Acquisition**: sourcing, screening, entrevistas, offer
2. **Compensação & Rewards**: bandas, mérito, equidade, propostas
3. **L&D / Performance**: avaliações, feedback, planos de desenvolvimento
4. **People Operations / Admin**: onboarding, offboarding, folha, dúvidas
5. **People Analytics / Decisão**: reporting, análise causa-raiz, predição

Cada área tem **3 perguntas** que checam:
1. Uso individual de IA (N1)
2. Existência de skills/workflows compartilhados (N2-N3)
3. IA propondo/tomando decisões (N4-N5)

## Scoring

- Cada resposta vale 1-5 (N1=1, N5=5)
- Nível por área = média das 3 respostas, arredondada
- Nível geral = mediana dos níveis das áreas (alinhado com "area-based progression")
- **Heatmap** mostra disparidade entre áreas, sinal crítico do framework
- **Trap detection**: se respostas indicam armadilhas conhecidas (ex: "medimos por tokens"), o report avisa

## Recomendações

Por área, mostramos:
- Nível atual da área
- Próxima fronteira (N+1) com o "sinal característico" pra reconhecer quando chegar lá
- Armadilha frequente daquela transição

A recomendação é específica pra HR e pra cada área (não genérica).
