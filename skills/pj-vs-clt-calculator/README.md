# pj-vs-clt-calculator

Skill gratuito do Claude para líderes de RH & People brasileiros. Calcula a equivalência salarial CLT ↔ PJ com cálculo fiscal completo (INSS, IRPF, FGTS, 13º, férias, benefícios, custos PJ). Use para comparar uma oferta individual ou processar em lote um CSV com vários candidatos.

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-pj-vs-clt-calculator)).

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

Instala o plugin `comp-skills` inteiro (4 skills, um dos quais é este).

## Uso

Basta falar com o Claude. Exemplos de prompts:

- "Quanto preciso faturar como PJ pra equivaler a um salário CLT de R$ 10.000?"
- "Qual o salário CLT equivalente a R$ 15.000 PJ com alíquota de 6%?"
- "Tenho uma planilha com 20 candidatos PJ, me ajuda a calcular o CLT equivalente de todos."

Para o modo batch, seu CSV precisa no mínimo de:
- `pj_billing` (R$/mês)
- `pj_aliquota` (%, ex: 6)

Colunas opcionais: `candidate_name`, `pj_invoices` (12/13), `pj_accounting`, `clt_vavr_desired`, `clt_bonus_desired`, `include_fgts` (1/0).

## O que é compartilhado com a Comp

Na primeira execução você será perguntado sobre:
1. Seu email (opcional): usado apenas para notificar atualizações do skill.
2. Telemetria anônima (default: off): se ativada, envia nome do skill, versão, um identificador anônimo de instalação e um timestamp por execução. **Nunca envia seus inputs ou outputs.**

Ambos ficam em `~/.comp-skills/config.json` localmente. Edite ou apague o arquivo a qualquer momento para revogar.

## Tabelas tributárias

As tabelas embarcadas são da Receita Federal 2024/2025. Publicamos uma versão nova anualmente em fevereiro quando as tabelas são atualizadas.

## Issues

Abra uma issue em [trycomp-io/comp-skills](https://github.com/trycomp-io/comp-skills/issues) com a label `eam`.

Powered by Comp · Free skills for HR & People leaders.
