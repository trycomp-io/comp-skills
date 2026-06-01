# Fontes Cobertas

## Academicas (via API)

| Fonte | API | Cobertura | Notas |
|---|---|---|---|
| OpenAlex | `https://api.openalex.org/works` | Maior base academica aberta (250M+ obras) | Inclui SSRN, NBER, journals indexados. Sem auth. Filtra por `from_publication_date` |
| arXiv | `http://export.arxiv.org/api/query` | Preprints, especialmente econ.GN, cs.AI, cs.CY | Sem auth, formato Atom XML |
| Semantic Scholar | `https://api.semanticscholar.org/graph/v1/paper/search` | Fallback se OpenAlex falhar | Rate limit baixo sem API key |

## Consultorias e Thought Leaders (via RSS / search)

| Fonte | Endpoint | Tipo |
|---|---|---|
| McKinsey Insights | `https://www.mckinsey.com/insights/rss` | RSS oficial |
| BCG Publications | site search com filtro de data | scraping leve |
| Deloitte Insights | `https://www2.deloitte.com/insights/us/en/feed.xml` | RSS |
| Gartner HR | blog feeds | RSS quando disponivel |
| Josh Bersin | `https://joshbersin.com/feed/` | RSS WordPress |
| MIT Sloan Review | `https://sloanreview.mit.edu/feed/` | RSS |
| Harvard Business Review | `https://hbr.org/the-magazine/rss` | RSS limitado |
| WTW Insights | site search | scraping leve |
| Mercer Insights | RSS quando disponivel | RSS |
| World Economic Forum | `https://www.weforum.org/agenda/rss.xml` | RSS, filtrar por tag |

## Criterio de Inclusao

Incluir:
- Papers academicos (peer review ou working paper) com abstract publico
- Relatorios de consultoria com metodologia explicita (n da amostra, fonte de dados)
- Surveys de mercado com escopo declarado
- Frameworks novos publicados por autores reconhecidos

Excluir:
- Marketing puro sem dado primario
- Posts curtos de opiniao sem fundamento
- Newsletter promocional
- Conteudo atras de paywall sem abstract publico (manter no apendice com badge `paywall`)

## Temas Cobertos

1. **Org Design**: span of control, layers, organizational structure, agile organizations, network organizations, holacracy, team design
2. **Workforce Planning**: strategic workforce planning, talent forecasting, headcount planning, skills-based organization, internal mobility
3. **IA & Forca de Trabalho**: generative AI productivity, task automation, occupation exposure to AI, augmentation vs substitution, AI adoption in HR, AI skills demand, future of work
