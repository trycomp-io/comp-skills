# Skills Gap Analysis

Analisa lacunas de capacidade da força de trabalho contra um conjunto de capacidades-alvo e recomenda **build / buy / borrow** por gap.

A partir de um inventário de skills (pessoa, skill, proficiência) e um conjunto de capacidades-alvo (skill, proficiência requerida, criticidade, headcount necessário), a skill calcula cobertura por skill, magnitude do gap e prioridade, e gera um relatório HTML executivo com:

- Heatmap skill × criticidade
- Lista priorizada de gaps com recomendação build/buy/borrow e rationale
- Resumo de implicações de hiring vs training

## Dual-mode

- **Claude Code**: roda o script Python e gera relatório HTML.
- **Claude Cowork**: análise inline no chat (aceita tabela colada ou descrição conversacional) com saída em markdown e artefato HTML quando disponível.

## Uso (Claude Code)

```bash
python3 scripts/skills_gap.py --inventory inventario.csv --target alvo.csv
```

**Inventário** (`inventario.csv`): `person`, `skill`, `proficiency` (1-5)

**Alvo** (`alvo.csv`): `skill`, `required_proficiency` (1-5), `criticality` (1-5), `headcount_needed`

## Lógica build/buy/borrow

| Ação | Quando |
|---|---|
| BUY (contratar) | gap grande + alta criticidade |
| BUILD (treinar) | já existe base interna parcial |
| BORROW (contractor/parceiro) | baixa criticidade ou demanda pontual |

## Privacidade

Processamento 100% local. Nenhum dado de colaborador sai da sua máquina.

---

Skill gratuita mantida pela [Comp](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skills-gap-analysis), ferramentas para times de RH e People.
