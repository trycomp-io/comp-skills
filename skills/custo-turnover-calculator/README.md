# custo-turnover-calculator

Skill gratuito do Claude para líderes de RH & People. Calcula o custo real (oculto) de turnover decompondo em 8 componentes: separação, recrutamento, onboarding, perda de produtividade no ramp, impacto no time, perda de conhecimento, impacto em cliente e erros/retrabalho.

Metodologia baseada no artigo da coluna Comp na Cajuína: [O custo oculto do turnover](https://cajuina.org/principais/coluna-comp/o-custo-oculto-do-turnover/).

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-custo-turnover-calculator)).

## Para que serve

CFO te pergunta: "quanto custa esse turnover de 18% no time de Eng?". Você precisa de um número defensável: não apenas a rescisão, mas o custo TOTAL: recruiter, onboarding, 6 meses de ramp sem produtividade plena, sobrecarga no time, conhecimento que saiu.

Útil para:
- Defender investimento em retenção (ROI de iniciativas anti-turnover)
- Estimar custo anual de turnover do time pro budget
- Priorizar quais cargos focar (top 5 mais caros de perder)
- Comparar cenários de uma reorg

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

Instala o plugin `comp-skills` inteiro.

## Uso

Basta falar com o Claude. Exemplos:

- "Quanto custa perder um Eng Manager de R$ 120k?"
- "Calcula o custo de turnover desses 5 desligamentos do último tri" (+ CSV)
- "Quanto vai me custar um turnover de 20% no time de vendas (12 SDRs a R$ 80k)?"
- "ROI de investir em retenção dos especialistas: custo de perder cada um vs custo do programa"

## Modos

| Modo | Quando |
|---|---|
| **Quick** | Você só sabe salário + nível. Tudo estimado via multiplicadores. |
| **Detailed** | Você tem números reais de algum(ns) componente(s). Mistura inputs + estimativas. |
| **Batch** | CSV com vários desligamentos. Útil pra reporting trimestral/anual. |

## Multiplicadores de referência

| Nível | Custo total ≈ % do salário anual |
|---|---|
| Operacional / Entry | 60% (50-75%) |
| Técnico / Especialista | 100% (80-125%) |
| Gerencial | 125% (100-150%) |
| Executivo / Senior Leadership | 200%+ |

Exemplo do artigo: gerente R$ 120k → R$ 86.5k de custo total (≈72%).

## Schema do CSV (batch)

Mínimo: `annual_salary`. Recomendado adicionar `level` e `role_label`. Veja [SKILL.md](SKILL.md) para schema completo (12 colunas opcionais).

## O que é compartilhado com a Comp

Na primeira execução você será perguntado sobre:
1. Seu email (opcional), usado apenas para notificar atualizações do skill.
2. Telemetria anônima (default: off): se ativada, envia nome do skill, versão, um identificador anônimo de instalação e um timestamp por execução. **Nunca envia salários, nomes ou valores informados.**

100% processamento local.

## Issues

Abra uma issue em [trycomp-io/comp-skills](https://github.com/trycomp-io/comp-skills/issues) com a label `eam`.

Powered by Comp · Free skills for HR & People leaders.
