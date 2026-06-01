# custo-demissao-calculator

Skill gratuito do Claude para líderes de RH & People brasileiros. Calcula o custo total de uma rescisão CLT, com decomposição completa de verbas (saldo, aviso, 13º, férias, FGTS, INSS, IRPF) e o custo total para o empregador.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-custo-demissao-calculator)).

## Para que serve

Você precisa estimar o impacto financeiro de uma rescisão (uma pessoa ou uma reorg inteira). O skill decompõe cada verba prevista em lei + os encargos do empregador (FGTS sobre rescisão, multas) e fecha com o custo total que sai do caixa.

Útil para:
- Decidir entre tipos de rescisão (sem justa causa vs acordo) antes de comunicar
- Estimar caixa para uma reorg / layoff round
- Validar cálculos da folha antes da homologação
- Simular cenários de "e se" pra People + CFO

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

Instala o plugin `comp-skills` inteiro (todos os skills da Comp).

## Uso

Basta falar com o Claude. Exemplos:

- "Quanto vai custar demitir um colaborador de R$ 10k, com 4 anos de casa, sem justa causa?"
- "Calcula a rescisão por acordo de um analista R$ 8k que entrou em março/2024"
- "Pedido de demissão de uma pessoa que não vai cumprir o aviso: quanto fica?"
- "Tabela com 5 cenários de rescisão pra eu apresentar pro CFO"

## Tipos de rescisão cobertos

| Tipo | Cenário |
|---|---|
| `sem_justa_causa` | Empregador demite sem motivo (aviso + 13º + férias + 40% FGTS) |
| `com_justa_causa` | Demissão por falta grave (apenas saldo + férias vencidas) |
| `pedido_demissao` | Colaborador pede para sair (sem multa, com 13º + férias) |
| `acordo` | Mútuo acordo, art. 484-A (50% aviso + 20% multa + 80% saque) |

## Metodologia

Baseada nas tabelas INSS/IRPF 2024/2025 da Receita Federal e nas regras da CLT vigente (Lei 12.506/2011 para aviso, Lei 13.467/2017 para acordo, etc.).

Cobre todos os componentes principais:
- Saldo de salário (proporcional aos dias trabalhados no mês)
- Aviso prévio (30 dias + 3/ano completo, capado em 90)
- 13º proporcional (1/12 por mês)
- Férias vencidas + 1/3 (se houver)
- Férias proporcionais + 1/3 (1/12 por mês do período aquisitivo)
- Multa FGTS (40% ou 20%)
- INSS + IRPF descontados (cálculo separado por verba)
- FGTS do empregador sobre verbas rescisórias

Saída inclui o custo total para o empregador, o líquido para o colaborador, e o saque FGTS disponível.

## O que NÃO está coberto (V1)

- Contratos por prazo determinado
- Estabilidades especiais (gestante, dirigente sindical, etc.)
- Indenização adicional por dispensa discriminatória
- Honorários de homologação sindical
- Seguro desemprego (é benefício, não custo direto do empregador)

Para esses casos, consulte seu departamento jurídico ou contábil.

## O que é compartilhado com a Comp

Na primeira execução você será perguntado sobre:
1. Seu email (opcional), usado apenas para notificar atualizações do skill.
2. Telemetria anônima (default: off): se ativada, envia nome do skill, versão, um identificador anônimo de instalação e um timestamp por execução. **Nunca envia salários, datas, nomes ou qualquer dado do cálculo.**

100% processamento local. Nada sai da sua máquina.

Ambos os opt-ins ficam em `~/.comp-skills/config.json` localmente. Edite ou apague o arquivo a qualquer momento para revogar.

## Atualizações de tabelas

As tabelas INSS/IRPF embarcadas são da Receita Federal 2024/2025. Publicamos versão nova anualmente em fevereiro quando as tabelas são atualizadas.

## Issues

Abra uma issue em [trycomp-io/comp-skills](https://github.com/trycomp-io/comp-skills/issues) com a label `eam`.

Powered by Comp · Free skills for HR & People leaders.
