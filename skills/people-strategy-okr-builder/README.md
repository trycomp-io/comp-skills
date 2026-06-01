# People Strategy & OKR Builder

Constrói a **estratégia de People na uma página** com OKRs amarrados à estratégia de negócio.

A partir de uma coleta conversacional (prioridades de negócio, dores de people, contexto de headcount/crescimento, horizonte, restrições), a skill gera um one-pager com:

- 3-5 prioridades estratégicas, cada uma ligada a um objetivo de negócio
- Por prioridade: Objective + 2-4 Key Results mensuráveis + iniciativas + owner + métrica
- Riscos e dependências
- Roadmap trimestral

## Dual-mode

- **Claude Code**: o agente coleta os inputs, monta o JSON e o script gera o one-pager HTML.
- **Claude Cowork**: o agente coleta conversacionalmente e produz markdown no chat, com artefato HTML quando disponível.

## Uso (Claude Code)

```bash
cat strategy.json | python3 scripts/build_strategy.py
```

O JSON de estratégia segue a estrutura documentada no `SKILL.md` (prioridades, objective, key results com target, iniciativas, owner, riscos, dependências, roadmap).

## Princípios

- Toda prioridade de People amarra a um objetivo de negócio.
- KRs são resultados mensuráveis com target e métrica, não atividades.
- Sempre inclui riscos, dependências e roadmap trimestral.

## Privacidade

Processamento 100% local.

---

Skill gratuita mantida pela [Comp](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=people-strategy-okr-builder), ferramentas para times de RH e People.
