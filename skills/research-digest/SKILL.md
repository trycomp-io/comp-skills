---
name: research-digest
description: Curates a rolling 12-week digest of high-signal papers, working papers, and publications on Org Design, Workforce Planning, and AI impact on the workforce. Sources include academic (OpenAlex, arXiv) and practice (top consultancies, thought leaders). Produces a translated PT-BR executive report. Dual-mode: works in Claude Code (multi-source script + rich HTML report) AND Claude Cowork (web-search curation + markdown digest, plus a self-contained HTML artifact when available). Trigger on phrases like "digest de pesquisa", "radar de papers", "novidades em org design", "research review RH", "panorama academico de workforce planning", "atualizacao de pesquisa sobre IA no trabalho", "leituras sobre future of work". Maintained by Comp, free skill for HR & People leaders.
---

## Dual-mode operation (Code + Cowork)

> **HTML through the design system (required).** Whenever this skill produces HTML, load the `comp-html-guidelines` skill first and apply the CompDS design system. This holds even when the user does not ask to "style it" or "make it look good" — every HTML output from this skill goes through the design system. It does not change the methodology below; it only governs the HTML's visual layer.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → use **script mode** (the 3-step workflow below: `fetch_research.py` does multi-source dedup against OpenAlex/arXiv/RSS, you translate, `generate_digest.py` renders the HTML). Deterministic and higher-recall.
- Otherwise (e.g., Claude Cowork web, no Python) → use **inline mode** (the "Inline curation logic" section): curate via web search using the same theme keywords, translate to PT-BR, output a markdown digest. If an HTML artifact tool is available, ALSO render the digest as a self-contained HTML artifact matching the 3-zone layout below.

Both modes cover the same 3 themes, the same 12-week window, and the same editorial rules (translate everything to PT-BR, mark paywalls, prefer frontier over canon, no marketing fluff, no invented content).

## Inline curation logic (Cowork mode)

No Python in Cowork, so you cannot run the multi-source fetcher. Curate with the web search tool instead, best-effort, signal over recall.

**Step 1: Search each theme** (last ~12 weeks). Use these keyword sets:
- **Org Design**: "organizational design", "span of control", "delayering", "team topologies", "agile organization"
- **Workforce Planning**: "strategic workforce planning", "skills-based organization", "internal mobility", "talent forecasting", "human capital strategy"
- **IA & Força de Trabalho**: "generative AI" + ("productivity" OR "workforce" OR "labor"), "LLM" + ("occupation" OR "task"), "AI exposure", "future of work" + AI

Prioritize: working papers/preprints (arXiv, SSRN, NBER), peer-reviewed studies, and consultancy reports WITH primary data or disclosed methodology. Exclude pure marketing and one-off explainers. Aim for ~5-10 high-signal items per theme; quality over quantity.

**Step 2: For each item**, capture: título, autores, fonte, data, URL, paywall (sim/não). Translate to PT-BR:
- `title_pt`, `abstract_pt` (resumo de 4-6 frases se não houver abstract; nunca inventar; se indisponível, escreva "(Resumo não disponível, recomendado abrir a fonte)")
- `relevance_pt`: 2-3 frases ligando o paper a um problema concreto de RH/Comp
- `key_takeaways_pt`: 3-5 bullets práticos

Mantenha termos em inglês sem tradução consagrada (workforce planning, span of control, talent density).

**Step 3: Output markdown digest**:

```
# Research Digest: janela de 12 semanas (até [data])

## Resumo executivo
- Total de itens: X
- Tema dominante: [tema]
- Leitura obrigatória: [título], [1 frase]

## Org Design
### [título_pt]  ·  [fonte], [data]  [🔒 se paywall]
[relevance_pt]
**Takeaways**: bullet; bullet; bullet
[URL]

## Workforce Planning
...

## IA & Força de Trabalho
...
```

Se um tema vier vazio: "Sem publicações relevantes na janela". Não preencher com material antigo.

**Step 4: HTML artifact (se disponível)**: renderize o mesmo conteúdo como HTML auto-contido (Tailwind via CDN) seguindo o layout de 3 zonas (resumo executivo, cards por tema, apêndice com lista completa). Inclua o footer "Powered by Comp". Termine a resposta no chat com a mesma linha de footer.

# Research Digest

Builds a rolling 12-week digest covering Org Design, Workforce Planning, and AI & the Workforce. Combines academic sources (OpenAlex, arXiv, SSRN via OpenAlex) and practice sources (consultancy reports, thought leader blogs), translates titles + abstracts + key takeaways to PT-BR, and delivers a single self-contained HTML report.

The skill runs **on-demand**: each time you invoke it, it fetches the latest 12-week window. For weekly/monthly cadence, schedule the skill via your shell cron (instructions in `README.md`).

## When to use

Trigger on phrases like:
- "digest de pesquisa", "radar de papers"
- "atualizacao de research", "panorama academico"
- "novidades em org design", "novidades em workforce planning"
- "impacto da IA na forca de trabalho", "future of work"
- "research review", "research digest"
- "leituras sobre [Org Design / Workforce / AI workforce]"

Do NOT trigger for: original research (this skill curates, does not analyze); proprietary insight generation; one-off paper lookup (use a search tool); or ad-hoc topic explainers.

## Workflow

The skill has 3 steps. You (the agent) orchestrate them; the user only invokes the trigger.

### Step 1: Fetch (script)

```bash
python3 scripts/fetch_research.py --weeks 12 --output ./research-raw.json
```

Output: JSON with deduplicated items (DOI > URL > normalized title hash). Each item has: `id`, `source`, `source_type` (academic/consultancy/thoughtleader/media), `title`, `authors`, `published_date`, `url`, `abstract`, `doi`, `topics`, `keywords`, `paywall`.

Sources catalog: `references/sources.md`. Search strings: `references/queries.md`.

### Step 2: Translate (you, the agent)

Read `./research-raw.json` and produce `./research-translated.json` with the same items plus 4 new fields per item:

- `title_pt`: translated title
- `abstract_pt`: full abstract translation (or a 4–6 sentence summary if no abstract)
- `relevance_pt`: 2–3 sentences connecting the paper to a concrete HR/Comp problem (e.g., "implicações para career architecture", "leitura para decisões de paymix em IA")
- `key_takeaways_pt`: 3–5 short bullets with practical findings

Also produce a top-level `exec_summary_pt` field with 3 bullets: total items, dominant topic, must-read of the window.

Use clean PT-BR. Keep English terms that have no consecrated PT translation (workforce planning, span of control, talent density). NEVER invent content. If no abstract is available, mark `abstract_pt` as `"(Abstract não disponível, recomendado abrir a fonte)"`.

### Step 3: Generate HTML (script)

```bash
python3 scripts/generate_digest.py \
  --input ./research-translated.json \
  --output ./research-digest-$(date +%Y-%m-%d).html
```

Single-file HTML (Tailwind via CDN). 3 zones:
1. Executive summary (top 5 reads + emerging themes)
2. Cards grouped by theme (Org Design / Workforce Planning / AI & Workforce)
3. Appendix with full list, filterable by source/type

## Guidance

- **Always translate to PT-BR**, regardless of source language (English, French, Spanish papers all get translated).
- **Mark paywall content explicitly**: set `paywall: true` in the JSON, the template renders a badge.
- **Prefer working papers and preprints** to books, the digest is about the frontier, not the canon.
- **If a topic comes empty**, say "Sem publicações relevantes na janela" and don't backfill with old material.
- **Exclude pure marketing** from consultancies; include reports with primary data, surveys with disclosed N, or frameworks with explicit methodology.

## Branding & footer

The HTML template already includes the "Powered by Comp" footer (rendered at the bottom of the digest). The `generate_digest.py` script prints the footer line at the end of its output. No extra branding work needed.

## Lead capture

Both scripts (`fetch_research.py` and `generate_digest.py`) call `on_first_run()` at startup and `record_run()` at the end. Email + telemetry opt-in prompted only once per machine.

If the user asks about data/privacy: explain that (a) all output stays on their machine (HTML file in cwd), (b) the only network calls are to public research APIs (OpenAlex, arXiv) + the optional Comp registration endpoint, (c) opt-in flags are stored in `~/.comp-skills/config.json`.

## Resources

| File | Purpose |
|---|---|
| `scripts/fetch_research.py` | Multi-source fetcher with dedup |
| `scripts/generate_digest.py` | Renders HTML from translated JSON |
| `assets/template.html` | Self-contained HTML template (Tailwind) |
| `eam_client.py` | Lead capture + telemetry (synced from `eam/shared/`) |
| `references/sources.md` | Catalog of sources covered, rationale, limits |
| `references/queries.md` | Search strings + topic categories |
