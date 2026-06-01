---
name: comp-html-guidelines
description: "Default skill for ALL HTML outputs from Comp skills. A lightweight, self-contained visual style guide (Comp palette black #1F1B17 + red #F4364C, DM Sans, near-white background, white cards, pill buttons, hero cover, Powered by Comp footer). MUST be loaded whenever a skill produces HTML, for any relatório, página, análise, dashboard, qualquer variação de \"faça/crie um html\", and for any \"apply the design\" / \"estiliza\" / \"padroniza\" / \"deixa isso bonito\" request on existing HTML. Apply it even when the user does not ask explicitly. Maintained by Comp, free skill for HR & People leaders."
---

# Comp HTML Guidelines

A lightweight, self-contained visual style guide for every HTML report, page, dashboard, or analysis produced by a Comp skill. Load it whenever you are about to write or restyle HTML so the result is consistent, polished, and on-brand. It does not change the methodology of the calling skill, it governs only the visual layer.

This is a Knowledge skill. The full rules live in `references/style-guide.md` and a ready-to-inline stylesheet lives in `assets/comp-base.css`. Read the style guide before writing HTML.

## When to use

- **Generate** — creating a new HTML report from scratch. Load `references/style-guide.md`, inline `assets/comp-base.css`, then build.
- **Apply** — the user has existing HTML and wants it styled ("estiliza", "padroniza", "deixa isso bonito", "apply the design"). Load the style guide and re-skin the markup, keeping the content.
- **Consult** — a question about a specific rule (color, layout, footer, chart). Answer from `references/style-guide.md`.

## The look in one paragraph

Near-white background (`#FAFAF8`), content in white cards with a hairline border and soft radius. Comp black (`#1F1B17`) for text and the hero, Comp red (`#F4364C`) as the single accent. DM Sans for everything. Generous spacing (24px rhythm). A hero band at the top with the report title and a short subtitle; a "Powered by Comp" footer at the bottom. One accent color only, semantic green/amber/red reserved for good/warning/bad states. No gradients, no decorative icons, no rainbow palettes.

## How to build

1. Read `references/style-guide.md` in full.
2. Start from the base scaffold in the style guide and inline `assets/comp-base.css` inside a `<style>` tag (copy it, do not link to a CDN for it).
3. Load DM Sans from Google Fonts and a charting library (Chart.js) from a CDN if you need charts.
4. Build the hero, then the content as cards / tables / stat cards, then the footer.
5. Run the self-review checklist at the end of the style guide before delivering.

## Escaping user data — required

Reports often embed data that originates from a user upload (names, areas, managers, free-text comments). When you inject any user-derived string into HTML — whether server-side in a script or client-side via `innerHTML` — escape it first (`& < > " '`). Never interpolate raw user text into markup. A name like `<img src=x onerror=...>` must render as literal text, not execute. When embedding a data blob in a `<script>` tag, also neutralize `</` (write it as `<\/`) so a value cannot close the script element.

## Completeness

Deliver the finished report the user asked for, not a sample or "v1". If the content is large, write it in full. If you cannot produce part of it, say so in your reply rather than shipping a placeholder card.

## Brand

- Hero: report title + subtitle. For a report about a specific company, use the logo URL and brand color the user provides; if none, use the company's initial in a tile. Never fabricate a logo.
- Footer: a "Powered by Comp" line linking to `comp.vc` with UTM params (see the style guide for the exact link). If you show the Comp logo mark, use the bundled inline SVG (`assets/comp-wordmark-white.svg` on dark/red, `assets/comp-wordmark-red.svg` on light) — never a scaled raster, a color-filtered PNG, or a hand-drawn mark (those come out jagged/off-brand). Style guide §7.

## Resources

| File | Purpose |
|---|---|
| `references/style-guide.md` | Palette, typography, spacing, components, charts, scaffold, self-review checklist. Read in full before writing HTML. |
| `assets/comp-base.css` | Ready-to-inline base stylesheet. Copy into a `<style>` tag in the output. |
| `assets/comp-wordmark-white.svg` | Official Comp wordmark (white) — inline in footers/hero on dark or red backgrounds. Crisp vector, no external host. |
| `assets/comp-wordmark-red.svg` | Official Comp wordmark (red `#F4364C`) — inline on white/light backgrounds. |
