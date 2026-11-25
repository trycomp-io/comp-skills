# zivo-html-guidelines

Skill gratuito do Claude que aplica um **guia visual leve e auto-contido** a qualquer saída HTML das skills da Zivo — relatórios, páginas, análises e dashboards. É a skill de estilo que padroniza a camada visual dos artefatos.

Mantido pela **Zivo** ([zivo.ai](https://zivo.ai?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-zivo-html-guidelines)).

## O que faz

Dá ao Claude um conjunto enxuto de regras e um CSS pronto pra deixar todo HTML consistente e bem-acabado:

- **Paleta**: ink `#1A1A1A`, off-white `#F1F1EA`, branco e um único vermelho `#F4364C` por tela
- **Tipografia**: Marcellus nos títulos e Source Sans 3 no texto (fallbacks oficiais da ABC Arizona), títulos em sentence case contando o achado
- **Componentes**: header row, hero, stat cards, tabelas, botões retos com seta, badges de status e footer "Powered by Zivo" com o wordmark oficial em SVG
- **Charts**: Chart.js com barras e pontos quadrados, série de cores da Zivo e um destaque em vermelho
- **Segurança**: exige escapar dados do usuário antes de injetar no HTML (anti-XSS)

Não embute biblioteca pesada nem dependência externa além das fontes do Google Fonts. O CSS base (`assets/zivo-base.css`) é copiado pra dentro do HTML gerado; páginas com Tailwind usam o tema `assets/zivo-tailwind.html`.

## Por que ela é default

As demais skills da Zivo acionam esta automaticamente sempre que produzem HTML. Você não precisa pedir "deixa bonito" ou "estiliza" — todo HTML passa pelo guia por padrão. Ative-a também sozinha pra criar um HTML do zero, padronizar um HTML existente, ou tirar dúvida sobre uma regra.

## Instalação

```bash
/plugin marketplace add trycomp-io/zivo-skills
/plugin install zivo-skills@zivo
```

## Uso

```
"Cria um relatório HTML de headcount com o visual da Zivo"
"Aplica o estilo da Zivo nesse HTML"
"Qual fonte uso nos títulos?"
```

## Conteúdo

| Arquivo | O que é |
|---|---|
| `SKILL.md` | Instruções e visão geral do guia |
| `references/style-guide.md` | Paleta, tipografia, espaçamento, componentes, charts, scaffold e checklist |
| `assets/zivo-base.css` | CSS base pronto pra inline no HTML gerado |
| `assets/zivo-tailwind.html` | Tema Tailwind (cantos retos, sem sombra, tokens e fontes Zivo) |
| `assets/zivo-wordmark-*.svg`, `assets/zivo-symbol-*.svg` | Wordmark e símbolo oficiais (Brand Center) |

## Issues

[trycomp-io/zivo-skills/issues](https://github.com/trycomp-io/zivo-skills/issues) com label `eam`.

Powered by Zivo, free skills for HR & People leaders.
