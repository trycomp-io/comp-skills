---
name: people-scorecard
description: Gera o pacote canônico mensal de People analytics a partir de um roster CSV (+ eventos opcional). Calcula headcount (total, por área, por nível), attrition anualizada (split lamentável se houver flag), tenure médio + distribuição, span of control (médio + distribuição), mobilidade interna (promoções), representatividade de gênero geral E em liderança com regra de confidencialidade (grupos < 3 suprimidos), taxa de novos contratados/crescimento, e tendência do período se os eventos tiverem datas. Output: scorecard executivo de uma página, o pacote que você entrega pro CEO. Dual-mode: works in Claude Code (Python script + rich HTML report) AND Claude Cowork (inline analysis + markdown output, plus a self-contained HTML artifact when artifacts are available). Trigger em "people scorecard", "pacote de people analytics", "dashboard de RH", "scorecard de pessoas", "people metrics", "indicadores de RH pro board", "headcount e attrition". Maintained by Comp, free skill for HR & People leaders.
---

## Dual-mode operation (Code + Cowork)

> **HTML through the design system (required).** Whenever this skill produces HTML, load the `comp-html-guidelines` skill first and apply the CompDS design system. This holds even when the user does not ask to "style it" or "make it look good" — every HTML output from this skill goes through the design system. It does not change the methodology below; it only governs the HTML's visual layer.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (deterministic, writes the rich HTML report). This is the existing workflow below.
- Otherwise (e.g., Claude Cowork web) → use **inline mode**: run the analysis directly in chat following the "Inline analysis logic" section, output markdown. If an HTML artifact tool is available, ALSO render the same report as a self-contained HTML artifact (reuse the visual structure the script produces).

Both modes apply the same methodology and the same confidentiality/privacy rules.

## Inline analysis logic (Cowork mode)

### Como o usuário fornece os dados
- **Roster** (atual): colunas `name`, `area`, `level`, `manager` (opc), `gender` (opc), `tenure_months` OU `hire_date`, `salary` (opc). Auto-detect com aliases PT/EN.
- **Eventos** (opcional): `type` (hire/exit/promotion), `date`, `regretted` (opc). Sem eventos, as taxas (attrition, mobilidade, crescimento) e a tendência são omitidas.
- Cole as tabelas no chat ou anexe os CSVs. Roster grande (>~50 linhas) é difícil de processar manualmente. Sugira rodar em Claude Code (script mode).
- **Salário/datas** em formato BR devem ser convertidos.

### Metodologia (fixa, idêntica ao script)
1. **Headcount**: total + contagem por área + por nível.
2. **Tenure**: se houver `tenure_months` use direto; senão derive de `hire_date` (meses até hoje). Reporte média, mediana e distribuição (0-12m / 12-24m / 24-48m / 48m+).
3. **Span of control** (se houver `manager`): conte reportes por gestor; reporte média, máx e distribuição (1-3 / 4-7 / 8-12 / 13+).
4. **Attrition anualizada** (precisa de eventos): `exits ÷ avg_headcount × (12 ÷ meses_do_período) × 100`. `avg_headcount ≈ headcount_atual + (exits − hires)/2`. Período inferido pelas datas dos eventos (default 12m). **Split lamentável** se houver flag `regretted`.
5. **Mobilidade interna**: `promoções ÷ headcount × 100`.
6. **Crescimento / novos contratados**: `(hires − exits) ÷ headcount × 100` e `hires ÷ headcount × 100`.
7. **Representatividade** (se houver `gender`): % por gênero geral E entre níveis de liderança (heurística: nível contém lead/head/manager/gestor/diretor/vp/chief/L5+ etc.). **Regra de confidencialidade: qualquer grupo de gênero com menos de 3 pessoas é suprimido (mostrado como "—") e não entra no cálculo de %.** Nunca baixe esse limite de 3, ele protege a privacidade individual. Idem para liderança: se o total de líderes < 3, suprima o bloco inteiro.
8. **Tendência**: se os eventos tiverem datas, agregue contratações/saídas/promoções por mês.

### Output markdown (Cowork mode)

```
## People Scorecard

**Headcount: N** · Attrition anual.: X% · Mobilidade interna: Y% · Tenure médio: Z meses · Span médio: W

### Headcount por área / por nível
| Área | HC | % |
|---|---|---|

### Tenure (distribuição)
| 0-12m | 12-24m | 24-48m | 48m+ |
|---|---|---|---|

### Span of control
| Reportes | Gestores |
|---|---|

### Representatividade (confidencialidade < 3 = "—")
| Gênero | Geral % | Liderança % |
|---|---|---|

### Tendência (se houver datas)
| Mês | Contratações | Saídas | Promoções |
|---|---|---|---|

### Insights
- ...
```

Encerre com: "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=chat-footer&utm_campaign=eam&utm_content=people-scorecard"

Se artefatos estiverem disponíveis, produza também uma versão HTML self-contained (Tailwind via CDN) espelhando o template do script: 6 tiles de KPI (headcount, áreas, attrition, mobilidade, tenure médio, span médio), resumo, tabelas de headcount por área/nível, distribuição de tenure e span, bloco de representatividade geral + liderança (com supressão), tendência mensal, footer Powered by Comp.

# People Scorecard

Roster CSV (+ eventos opcional) → scorecard executivo de uma página com headcount, attrition, tenure, span of control, mobilidade interna e representatividade. O pacote que você entrega pro CEO.

## Quando usar

Ativa em frases como:
- "people scorecard" / "pacote de people analytics" / "people metrics"
- "dashboard de RH" / "indicadores de RH pro board"
- "headcount e attrition" / "scorecard de pessoas"

## Workflow

**Step 1**: Pegue o roster CSV (mínimo `name`; idealmente `area`, `level`, `tenure_months`/`hire_date`, `manager`, `gender`). Opcional: events CSV (`type`, `date`, `regretted`).

**Step 2**:
```bash
python3 scripts/people_scorecard.py --roster roster.csv --events events.csv
```
(`--events` é opcional; sem ele, as taxas e a tendência são omitidas.)

**Step 3**: Apresente os KPI tiles + breakdowns. Destaque attrition, mobilidade e representatividade. Lembre que grupos < 3 são suprimidos.

## Regra de confidencialidade

Qualquer grupo de gênero com menos de 3 pessoas é suprimido ("—") e não entra no cálculo de representatividade. Nunca baixe esse limite de 3, ele protege a privacidade individual.

## Privacidade

Processamento 100% local. O roster nunca sai da máquina.

## Lead capture

`eam_client.py` (raiz da skill): `on_first_run()` 1x por máquina + `record_run()` por execução. Email opcional + telemetria opt-in. Nunca envia o roster.

## Resources

| File | Purpose |
|---|---|
| `scripts/people_scorecard.py` | Cálculos + HTML dashboard |
| `eam_client.py` | Lead capture + telemetria (sync de `eam/shared/`) |
