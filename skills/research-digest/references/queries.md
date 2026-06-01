# Queries por Tema

## Org Design

**OpenAlex concepts**: `organizational design`, `organizational structure`, `span of control`, `team design`
**arXiv categories**: `econ.GN`, `cs.CY`
**Keywords (OR)**:
- "organizational design"
- "org design"
- "span of control"
- "organizational structure"
- "delayering"
- "agile organization"
- "holacracy"
- "team topologies"

## Workforce Planning

**OpenAlex concepts**: `workforce planning`, `human resource planning`, `talent management`
**Keywords**:
- "workforce planning"
- "strategic workforce planning"
- "skills-based organization"
- "internal mobility"
- "talent forecasting"
- "headcount planning"
- "human capital strategy"

## IA & Forca de Trabalho

**OpenAlex concepts**: `artificial intelligence`, `labor economics`, `automation`
**arXiv categories**: `cs.AI`, `econ.GN`, `cs.CY`
**Keywords**:
- "generative AI" AND ("productivity" OR "workforce" OR "labor")
- "large language model" AND ("occupation" OR "task" OR "job")
- "AI exposure"
- "AI augmentation"
- "automation labor"
- "future of work" AND ("AI" OR "artificial intelligence")
- "skills demand" AND "AI"

## Combinacao

Para cada tema, o `fetch_research.py` faz:
1. Query OpenAlex com filtro `from_publication_date:YYYY-MM-DD` (84 dias atras)
2. Query arXiv com `submittedDate:[YYYYMMDD0000 TO YYYYMMDD2359]`
3. Pull dos RSS feeds e filtra publicacoes na janela

Cada item recebe `topic` baseado em qual query trouxe (item pode aparecer em mais de uma; nesse caso, marca `topic` como lista).

## Limites

- OpenAlex: 25 itens por query x 3 temas = 75 max
- arXiv: 50 itens por query x 3 temas = 150 max
- RSS: todos os items publicados na janela
- Apos dedup, expectativa: 60-120 itens unicos por digest semanal
