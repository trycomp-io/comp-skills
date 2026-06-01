# comp-level-simulator

Skill gratuito do Claude para líderes de RH & People. Gera um simulador HTML interativo e auto-contido para avaliar níveis de cargo (L1–L6) usando a metodologia Comp: 4 pilares (Influência, Autonomia, Complexidade, Responsabilidade), 8 perguntas, escala A–E.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-comp-level-simulator)).

## O que faz

Gera um arquivo HTML por execução. Abra em qualquer navegador e ele te guia (ou quem você compartilhar) por 8 perguntas e devolve um nível calibrado. O arquivo é auto-contido: sem backend, sem dados enviados pra fora, funciona offline depois de gerado.

Use para:
- Padronizar decisões de leveling no time todo
- Entregar aos gestores uma ferramenta self-service pra avaliar novas posições
- Remover viés (salário, título, tempo de casa) das conversas de nível
- Validar uma proposta de leveling de RH/Talent antes de publicar

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

Instala o plugin `comp-skills` inteiro (4 skills, um dos quais é este).

## Uso

Basta falar com o Claude. Exemplos:

- "Gera um simulador de nível pra eu mandar pros gestores"
- "Quero avaliar o nível dessa nova posição de Eng Manager"
- "Como nivelar uma posição? Tem uma ferramenta?"
- "Padroniza a avaliação de level aqui na empresa"

O Claude gera um `Comp-Level-Simulator-{timestamp}.html` no diretório atual. Abre no navegador, compartilha via Drive/email ou hospeda onde quiser.

## Metodologia

| Pilar | Perguntas | Score por pergunta (A→E) |
|---|---|---|
| Influência | 2 | 5, 4, 3, 2, 1 |
| Autonomia | 2 | 5, 4, 3, 2, 1 |
| Complexidade | 2 | 5, 4, 3, 2, 1 |
| Responsabilidade | 2 | 5, 4, 3, 2, 1 |

Total: 8–40. Mapeia para L1 (Júnior) → L6 (Especialista Sênior / Gerente Sênior). L5–L6 ficam comprimidos no topo: chegar a níveis executivos exige scores consistentemente altos em todos os pilares.

## O que é compartilhado com a Comp

Na primeira execução você será perguntado sobre:
1. Seu email (opcional), usado apenas para notificar atualizações do skill.
2. Telemetria anônima (default: off): se ativada, envia nome do skill, versão, um identificador anônimo de instalação e um timestamp por execução. **Nunca envia seus inputs nem o HTML que você gera.**

O HTML em si **nunca** chama o servidor. É JS puro client-side. Tudo que você preenche fica no navegador.

Ambos os opt-ins ficam em `~/.comp-skills/config.json` localmente. Edite ou apague o arquivo a qualquer momento para revogar.

## Issues

Abra uma issue em [trycomp-io/comp-skills](https://github.com/trycomp-io/comp-skills/issues) com a label `eam`.

Powered by Comp · Free skills for HR & People leaders.
