# job-profile-builder

Skill gratuito do Claude para HR/Recruiter/Hiring Manager. Conduz uma entrevista estruturada com o hiring manager e gera um pacote completo de abertura de vaga: JD + scorecard + roteiro de entrevistas.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-job-profile-builder)).

## O que faz

Em vez de receber uma JD ruim do hiring manager e ter que reescrever 3 vezes, você (recruiter/RH) usa o skill com o hiring manager presente:

1. Claude faz 10-15 perguntas estruturadas (4 blocos: contexto, outcomes, filtros, processo)
2. Hiring manager responde conversacionalmente
3. Skill gera HTML + Markdown com:
   - **Resumo executivo** (por que agora, outcomes em 6 meses, deal-breakers)
   - **JD completa** (sobre a vaga, responsabilidades, requisitos, nice-to-have, oferta)
   - **Scorecard** ponderado por critério, com rubrica
   - **Roteiro de entrevistas** por estágio com "o que procurar"

Vira o ponto de partida pro processo inteiro: recruiter pega o HTML, ajusta pra plataforma de vagas; entrevistadores usam o scorecard; hiring manager assina embaixo do alinhamento que ele mesmo deu.

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Vou abrir uma vaga de Engineering Manager, me ajuda a entrevistar o hiring manager"
"Cria um job profile pra Head of Marketing"
"Estruturar perfil da vaga de Senior Designer"
```

## O que vai no pacote

- Resumo executivo (por que essa vaga agora, outcomes em 6 meses, deal-breakers)
- JD pronta pra usar
- Scorecard ponderado (5-8 critérios, com rubrica por nível)
- Roteiro de entrevistas (perguntas por estágio + "o que procurar")

## O que é compartilhado com a Comp

Email opcional + telemetria opt-in. **Nunca** envia conteúdo da JD, respostas do hiring manager ou nomes.

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp · Free skills for HR & People leaders.
