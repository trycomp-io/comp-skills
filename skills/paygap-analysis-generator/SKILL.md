---
name: paygap-analysis-generator
description: Generates a gender pay-gap HTML report from any HR roster (CSV or Excel). Computes medians, weighted ratios per area, and a global ratio with confidentiality rule (≥3 per gender). Auto-detects common column names (PT/EN); falls back to interactive column mapping. Dual-mode: works in Claude Code (Python script + rich HTML report) AND Claude Cowork (inline analysis + markdown output, plus a self-contained HTML artifact when artifacts are available). Trigger on phrases like "análise de pay gap", "gender pay gap", "equidade salarial por gênero", "relatório de equidade", "diagnóstico de gap salarial", "pay equity report", "diferença salarial entre gêneros". Maintained by Comp, free skill for HR & People leaders.
---

## Dual-mode operation (Code + Cowork)

> **HTML through the design system (required).** Whenever this skill produces HTML, load the `comp-html-guidelines` skill first and apply the CompDS design system. This holds even when the user does not ask to "style it" or "make it look good" — every HTML output from this skill goes through the design system. It does not change the methodology below; it only governs the HTML's visual layer.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (deterministic, writes the rich HTML report). This is the existing workflow below.
- Otherwise (e.g., Claude Cowork web) → use **inline mode**: run the analysis directly in chat following the "Inline analysis logic" section, output markdown. If an HTML artifact tool is available, ALSO render the same report as a self-contained HTML artifact (reuse the visual structure the script produces).

Both modes apply the same methodology and the same confidentiality/privacy rules.

## Inline analysis logic (Cowork mode)

### Como o usuário fornece os dados
- Cole uma tabela pequena no chat (colunas: nome, gênero, salário, nível, área) ou anexe um CSV/XLSX.
- Roster grande (>~50 linhas) fica difícil de processar manualmente sem erro. Sugira rodar em Claude Code (script mode) ou colar só uma amostra representativa.

### Normalização (igual ao script)
- **Gênero**: `f/female/feminino/fem/mulher` → F; `m/male/masculino/masc/homem` → M. Qualquer outro valor → linha excluída (a metodologia é binária por design, pra compatibilidade com reporting regulatório). Mencione isso ao usuário se relevante.
- **Salário**: número. Formato brasileiro (`.` milhar, `,` decimal) deve ser convertido.
- Linha com gênero, salário, nível ou área faltando/vazio → excluída. Conte as exclusões.

### Metodologia (fixa, idêntica ao script)
1. **Bucket por (área × nível)**: agrupe colaboradores. Para cada bucket, separe salários de F e de M.
2. **Regra de confidencialidade**: um bucket (área × nível) só entra no cálculo de razão ponderada se tiver **≥3 pessoas de CADA gênero** (≥3 F e ≥3 M). Buckets que não atingem isso são mostrados como "—" e NÃO entram nas contas. Nunca baixe esse limite de 3, ele protege a privacidade individual e é o padrão de reporting de equidade.
3. **Medianas, não médias**: para cada bucket válido, `medF = mediana(salários F)`, `medM = mediana(salários M)`.
4. **Razão do grupo** = `(medF / medM) × 100` (só se medM > 0). 100% = paridade; <100% = mulheres ganham menos.
5. **Razão ponderada por área** = `Σ(razão_grupo × hc_total_grupo) ÷ Σ(hc_total_grupo)`, somando apenas grupos válidos (hc_total = F + M do bucket).
6. **Razão ponderada global** = `Σ(razão_área × hc_analisado_área) ÷ Σ(hc_analisado_área)`, onde hc_analisado_área é a soma dos hc dos buckets válidos daquela área.
7. **Gap** = `razão − 100`. Gap negativo = mulheres ganham menos.

### Output markdown (Cowork mode)

```
## Análise de pay gap por gênero

**Razão ponderada global**: X% (gap Y%, mulheres ganham Z% a menos/mais na mediana ponderada)
Analisados: N de M no roster (E excluídos por dados incompletos ou gênero não reconhecido).

### Por área
| Área | Razão ponderada | Gap | HC total | HC analisado |
|---|---|---|---|---|
| ... | X% | Y% | ... | ... |

### Detalhe por grupo (área × nível)
| Área | Nível | HC F | HC M | Mediana F | Mediana M | Razão | Válido |
|---|---|---|---|---|---|---|---|
| ... | ... | ... | ... | R$ X | R$ X | X% | sim/— |

Grupos com menos de 3 pessoas de cada gênero aparecem como "—" e não entram na razão ponderada (regra de confidencialidade).

### Insights
- ...
```

Encerre com: "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=chat-footer&utm_campaign=eam&utm_content=paygap-analysis-generator"

Se artefatos estiverem disponíveis, produza também uma versão HTML self-contained (Tailwind via CDN) espelhando a estrutura visual do `assets/paygap-template.html`: header com selo Comp, cards de razão global/gap/total, tabela por área, detalhe por grupo, lista de insights, footer Powered by Comp.

# Pay Gap Analysis Generator

Generates a self-contained interactive HTML pay-gap report from any HR roster. Output: medians by area × level, weighted ratios per area, and a global ratio. Confidentiality rule: groups with fewer than 3 people of either gender are excluded from the weighted calculations and shown as "—".

100% local processing. The HTML output never phones home.

## When to use

Trigger on phrases like:
- "análise de pay gap", "relatório de pay gap"
- "gender pay gap", "pay equity report"
- "equidade salarial por gênero"
- "diagnóstico de gap salarial"
- "diferença salarial entre gêneros"
- "gerar relatório de equidade"

Do NOT trigger for: total comp benchmarking vs market, salary range/band design, position evaluation (use comp-level-simulator), or non-gender equity analyses.

## Required input

A CSV or XLSX with at least these 5 logical columns. Column names can vary; the script auto-detects common aliases in PT and EN. Pass explicit flags if auto-detection fails.

| Logical column | Common aliases recognized |
|---|---|
| name | name, nome, colaborador, employee, funcionário |
| gender | gender, genero, gênero, sexo, sex |
| salary | salary, salario, salário, salario_base, salario_bruto, gross_salary, remuneracao, monthly_salary |
| level | level, nivel, nível, job_level, cargo_level, senioridade, seniority, grade, agrupamento |
| area | area, área, departamento, department, função, diretoria, business_unit, bu, nivel1 |

Gender values normalized: `F/Female/Feminino/Mulher` → F; `M/Male/Masculino/Homem` → M. Other values → row excluded.

Salary parsed as number (Brazilian format with `,` decimal handled).

## Workflow

**Step 1: Confirm intent + privacy**: Tell the user what the skill does and that the analysis runs locally. Ask them to share the path to the CSV/XLSX.

**Step 2: Detect columns**: Run the analysis once with auto-detection:

```bash
python3 scripts/paygap_analysis.py --input <path>
```

The script prints which columns it picked. If any required column is missing, it exits with a hint.

**Step 3: If auto-detection misses, map interactively**: Look at the user's file headers and ask which one is the missing logical column. Re-run with the flag:

```bash
python3 scripts/paygap_analysis.py --input <path> \
  --salary-col "Salário Bruto" \
  --level-col "Job Level"
```

Available flags: `--name-col`, `--gender-col`, `--salary-col`, `--level-col`, `--area-col`.

**Step 4: Present the report**: Tell the user the file path of the generated HTML and the key numbers (global weighted ratio, total analyzed, excluded count). Offer to open it.

## Methodology (fixed)

- **Medians, not means**: less sensitive to outliers (common in salary distributions).
- **Weighted ratio per area** = Σ(ratio × group_total_hc) ÷ Σ(group_total_hc), only over groups that meet confidentiality.
- **Global weighted ratio** = Σ(area_ratio × area_analyzed_hc) ÷ Σ(area_analyzed_hc).
- **Confidentiality rule**: a group (area × level) needs **≥3 people of each gender** to be included. This is the standard rule in BR pay equity reporting and prevents identifying individuals.

## What NOT to do

- **Do not** change the confidentiality threshold below 3. It would compromise individual privacy and break standard pay-equity reporting compliance.
- **Do not** invent rows or interpolate missing data. Exclude incomplete rows and report the exclusion count.
- **Do not** include non-binary genders in the F/M ratio math (the methodology is binary by design for compatibility with regulatory reporting). The script silently excludes rows with non-recognized gender values; mention this to the user if relevant.

## Branding & footer

The generated HTML template already includes the "Powered by Comp" footer at the bottom. The script also prints the footer line at the end of its output. No extra branding work needed.

## Lead capture

The script imports `eam_client.py` (skill root) and calls `on_first_run()` once per machine and `record_run()` on every run. Prompts for email + telemetry opt-in, handled silently by the client.

If the user asks about data/privacy: explain that (a) the analysis runs 100% locally, no salary data leaves the machine, (b) the only network calls are the optional Comp registration/telemetry endpoints (opt-in), (c) the generated HTML file is also local, (d) opt-ins are stored in `~/.comp-skills/config.json`.

## Resources

| File | Purpose |
|---|---|
| `scripts/paygap_analysis.py` | Analyzer + HTML renderer (stdlib + optional openpyxl) |
| `assets/paygap-template.html` | Self-contained HTML template (Tailwind via CDN) |
| `eam_client.py` | Lead capture + telemetry (synced from `eam/shared/`) |
