# candidate-screening

Skill gratuito do Claude para Recruiter/RH/Hiring Manager. Avalia candidatos contra o scorecard de uma vaga e devolve ranking + justificativa por critério + recomendação (entrevistar / phone screen / declinar).

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-candidate-screening)).

## O que faz

Você dá:
1. Critérios da vaga (scorecard do `job-profile-builder` ou seus)
2. Lista de candidatos (paste, CSV, PDF, transcrição)

Skill devolve:
- **Ranking HTML** com tabela de scores
- **Card detalhado por candidato** (score por critério + justificativa + flags + recomendação)
- **Markdown editável** pra ajustar e enviar pro hiring manager

Reduz screening de horas pra minutos mantendo defensabilidade: cada score tem evidência citada.

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Ranqueia esses 8 candidatos contra a vaga de Eng Manager"
"Shortlist pra Head of Marketing, recebi 15 perfis do LinkedIn"
"Avalia esses CVs contra meu scorecard"
```

Funciona melhor combinado com `job-profile-builder`: usa o scorecard daquele skill direto.

## Recomendações disponíveis

- **Entrevistar**: top tier, manda pra hiring manager
- **Phone screen**: promissor, vale 30min de validação
- **Declinar**: gap claro, com justificativa por critério
- **Revisar**: caso ambíguo, pedir mais contexto

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia dados dos candidatos, perfis ou avaliações.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
