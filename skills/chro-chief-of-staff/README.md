# chro-chief-of-staff

Skill gratuito do Claude, o **Chief of Staff conversacional do CHRO**. Mantém contexto persistente (stakeholders, cadências, calendário, open loops) e ajuda com pré-meeting briefs, visão semanal, drafts de comunicação, strategic prompts e orquestração com os outros skills da Comp.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-chro-chief-of-staff)).

## O que faz

Não substitui o CHRO, maestra. Em vez de você refazer o mesmo prep pra cada 1:1 com CEO, esse skill mantém o contexto e te dá:

- **Pré-meeting briefs**: pra qualquer reunião (1:1 CEO, ELT, board, comp committee)
- **Visão semanal**: o que vem essa semana + 2 semanas à frente + open loops em risco
- **Drafts de comunicação**: email/Slack/memo pra qualquer stakeholder, tom calibrado por relação
- **Strategic prompts**: "comp cycle em 4 semanas, deveria estar X"
- **Open loops tracker**: persiste action items, decisões pendentes
- **Orquestração**: sabe quando recomendar `paygap-analysis`, `regretted-attrition`, `board-slide` etc.

Tudo bilíngue (PT-BR + EN, configurável).

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Primeira execução: setup

```bash
python3 ~/.claude/plugins/.../scripts/chro_cos.py setup
```

Wizard interativo coleta nome, empresa, idioma, stakeholders (CEO/CFO/peers/diretos), eventos do calendário próximos.

Config persiste em `~/.comp-skills/chro-context.json`, e todas as próximas execuções leem dele.

## Uso

```
"Me dá o brief do 1:1 com CEO amanhã"
"Como tá minha semana?"
"Drafta um email pro CFO sobre o comp budget"
"O que devo estar pensando agora?"
"Adiciona um loop: aprovar reorg do time Eng até 15/06"
"Quais open loops em aberto?"
```

## O que NÃO faz

- Não envia emails/Slack diretamente (você revisa e envia)
- Não acessa seu calendar real (você atualiza a config manualmente OU edita o JSON)
- Não substitui análises (delega pros skills especializados)
- Sem backend cloud, tudo local

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia contexto, briefs, drafts, loops ou stakeholders.

100% local. Config no seu `~/.comp-skills/chro-context.json`.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
