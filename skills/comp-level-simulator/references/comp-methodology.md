# Comp Level Methodology Reference

## 4 Pilares (2 perguntas cada = 8 total)

**Influencia** - Impacto nas decisoes e estrategias da organizacao
1. O trabalho do individuo impacta as decisoes e estrategias em toda a empresa?
2. O individuo pode iniciar e liderar mudancas em todo o departamento sem aprovacao previa?

**Autonomia** - Capacidade de agir sem supervisao
1. O individuo trabalha sem supervisao?
2. O individuo pode definir suas proprias metas e prazos?

**Complexidade** - Analise e resolucao de problemas
1. O trabalho do individuo envolve lidar com projetos interdepartamentais?
2. O individuo e responsavel por resolver problemas complexos que afetam os resultados do negocio?

**Responsabilidade** - Obrigacoes por pessoas, resultados e recursos
1. O individuo e responsavel por gerenciar um orcamento ou recursos?
2. O papel do individuo envolve liderar equipes ou projetos?

## Escala de Respostas (por pergunta)

| Opcao | Score | Significado |
|-------|-------|-------------|
| A | 5 | Sempre / 100% / Grande escala |
| B | 4 | Frequentemente / ~75% / Escala moderada |
| C | 3 | Ocasionalmente / ~50% / Pequena escala |
| D | 2 | Raramente / ~25% / Muito pouco |
| E | 1 | Nunca / 0% / Nao se aplica |

## Faixas Padrao (score total 8-40)

| Score | Level | Titulo |
|-------|-------|--------|
| >= 39 | L6 | Gerente Senior / Especialista III |
| >= 36 | L5 | Gerente / Especialista II |
| >= 32 | L4 | Coordenador / Especialista I |
| >= 24 | L3 | Supervisor / Senior |
| >= 16 | L2 | Pleno |
| >= 8  | L1 | Junior |

## Correspondencia Master List

| Level | IC | MGMT | CGL |
|-------|----|------|-----|
| L1 | Junior | - | 1 |
| L2 | Pleno | - | 2 |
| L3 | Senior | Supervisor | 3 |
| L4 | Especialista | Coordenador | 4 |
| L5 | Especialista II | Gerente | 5 |
| L6 | Especialista III | Gerente Senior | 6 |

## Distribuicao Proporcional das Faixas

As faixas seguem esta distribuicao no range (minScore ate maxScore):

| Level | Posicao no range |
|-------|-----------------|
| L1 | 0% (minScore) |
| L2 | 25% |
| L3 | 50% |
| L4 | 75% |
| L5 | 87.5% |
| L6 | 93.75% |

L1 a L4 sobem linearmente (25% cada). L5 e L6 ficam comprimidos no topo - chegar a niveis executivos exige scores consistentemente altos em todos os pilares.

## Barra de Progresso

```
percentage = ((score - minScore) / (maxScore - minScore)) * 100
// Clamp entre 0% e 100%
```
