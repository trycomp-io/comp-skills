# comp-html-guidelines

Skill gratuito do Claude que aplica um **guia visual leve e auto-contido** a qualquer saída HTML das skills da Comp — relatórios, páginas, análises e dashboards. É a skill de estilo que padroniza a camada visual dos artefatos.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-comp-html-guidelines)).

## O que faz

Dá ao Claude um conjunto enxuto de regras e um CSS pronto pra deixar todo HTML consistente e bem-acabado:

- **Paleta**: preto `#1F1B17` + vermelho `#F4364C` como único acento, fundo near-white, cards brancos com borda fina
- **Tipografia**: DM Sans, ritmo de espaçamento de 24px
- **Componentes**: hero, stat cards, tabelas, botões pill, badges e footer "Powered by Comp"
- **Charts**: orientação pra usar Chart.js com a paleta da marca
- **Segurança**: exige escapar dados do usuário antes de injetar no HTML (anti-XSS)

Não embute biblioteca pesada nem dependência externa além da fonte DM Sans. O CSS base (`assets/comp-base.css`) é copiado pra dentro do HTML gerado.

## Por que ela é default

As demais skills da Comp acionam esta automaticamente sempre que produzem HTML. Você não precisa pedir "deixa bonito" ou "estiliza" — todo HTML passa pelo guia por padrão. Ative-a também sozinha pra criar um HTML do zero, padronizar um HTML existente, ou tirar dúvida sobre uma regra.

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

## Uso

```
"Cria um relatório HTML de headcount com o visual da Comp"
"Aplica o estilo da Comp nesse HTML"
"Qual a cor de destaque do hero?"
```

## Conteúdo

| Arquivo | O que é |
|---|---|
| `SKILL.md` | Instruções e visão geral do guia |
| `references/style-guide.md` | Paleta, tipografia, espaçamento, componentes, charts, scaffold e checklist |
| `assets/comp-base.css` | CSS base pronto pra inline no HTML gerado |

## Issues

[trycomp-io/comp-skills/issues](https://github.com/trycomp-io/comp-skills/issues) com label `eam`.

Powered by Comp, free skills for HR & People leaders.
