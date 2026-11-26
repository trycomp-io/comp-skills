---
name: zivo-html-guidelines
description: "Default skill for ALL HTML outputs from Zivo skills. A self-contained visual style guide that follows the Zivo brand (ink #1A1A1A, off-white #F1F1EA, white, a single red #F4364C highlight, Marcellus + Source Sans 3 as fallbacks for ABC Arizona, square corners, no shadows or gradients, the official Zivo wordmark as inline SVG in a Powered by Zivo footer). MUST be loaded whenever a skill produces HTML, for any relatório, página, análise, dashboard, qualquer variação de \"faça/crie um html\", and for any \"apply the design\" / \"estiliza\" / \"padroniza\" / \"deixa isso bonito\" request on existing HTML. Apply it even when the user does not ask explicitly. Maintained by Zivo, free skill for HR & People leaders."
---

# Zivo HTML Guidelines

A lightweight, self-contained visual style guide for every HTML report, page, dashboard, or analysis produced by a Zivo skill. Load it whenever you are about to write or restyle HTML so the result is consistent, polished, and on-brand. It does not change the methodology of the calling skill, it governs only the visual layer.

This is a Knowledge skill. The full rules live in `references/style-guide.md`, a ready-to-inline stylesheet lives in `assets/zivo-base.css`, and `assets/zivo-tailwind.html` themes pages that use the Tailwind CDN. Read the style guide before writing HTML.

## When to use

- **Generate**: creating a new HTML report from scratch. Load `references/style-guide.md`, inline `assets/zivo-base.css`, then build.
- **Apply**: the user has existing HTML and wants it styled ("estiliza", "padroniza", "deixa isso bonito", "apply the design"). Load the style guide and re-skin the markup, keeping the content.
- **Consult**: a question about a specific rule (colour, layout, footer, chart). Answer from `references/style-guide.md`.

## The look in one paragraph

Off-white page (`#F1F1EA`), content in white cards with a hairline ink border and square corners. Ink (`#1A1A1A`) for text and the hero band. Red (`#F4364C`) appears once per view: the hero's square start node, the one highlighted figure, or the one primary button. Headlines in Marcellus (fallback for ABC Arizona Flare), regular weight, sentence case, stating the finding; text in Source Sans 3 (fallback for ABC Arizona Sans). A header row of small capital captions over a hairline rule opens the hero; the official Zivo wordmark closes the page bottom-left in a "Powered by Zivo" footer. No shadows, gradients, rounded corners, emoji or decorative icons; status colours only for states, the six-colour Zivo series only in charts.

## How to build

1. Read `references/style-guide.md` in full.
2. Start from the scaffold in the style guide (§8) and inline `assets/zivo-base.css` inside a `<style>` tag (copy it, do not link to it). For Tailwind pages, paste `assets/zivo-tailwind.html` after the Tailwind script instead.
3. Load Marcellus + Source Sans 3 from Google Fonts and Chart.js from a CDN if you need charts.
4. Build the hero (header row, finding, subtitle), then the content as cards / tables / stat cards, then the footer with the inline wordmark.
5. Run the self-review checklist at the end of the style guide before delivering.

## Escaping user data (required)

Reports often embed data that originates from a user upload (names, areas, managers, free-text comments). When you inject any user-derived string into HTML, whether server-side in a script or client-side via `innerHTML`, escape it first (`& < > " '`). Never interpolate raw user text into markup. A name like `<img src=x onerror=...>` must render as literal text, not execute. When embedding a data blob in a `<script>` tag, also neutralize `</` (write it as `<\/`) so a value cannot close the script element.

## Completeness

Deliver the finished report the user asked for, not a sample or "v1". If the content is large, write it in full. If you cannot produce part of it, say so in your reply rather than shipping a placeholder card.

## Brand

- Write "Zivo" in text and "AI-native" with a lowercase n. Never type "ZIVO"; the capitalised form exists only as the drawn wordmark.
- Hero: header row + the finding + one subtitle line. For a report about a specific company, show the logo URL the user provides in a square tile; if none, use the company's initial. Never fabricate a logo.
- Footer: the Zivo wordmark (inline SVG) bottom-left plus "Powered by Zivo · free skills for HR & People leaders", linking to `zivo.ai` with UTM params (style guide §7). Use the bundled SVGs only: never a raster, a colour-filtered image, an external image host or a wordmark typed in a font.

## Resources

| File | Purpose |
|---|---|
| `references/style-guide.md` | Palette, typography, writing, layout, components, charts, logo, scaffold, self-review checklist. Read in full before writing HTML. |
| `assets/zivo-base.css` | Ready-to-inline base stylesheet. Copy into a `<style>` tag in the output. |
| `assets/zivo-example.html` | Finished reference report applying every rule. Open it to see the target look. |
| `assets/zivo-tailwind.html` | Tailwind CDN theme (square radii, no shadows, Zivo tokens and fonts). Paste after the Tailwind script. |
| `assets/zivo-wordmark-ink.svg` | Official wordmark, ink. Default on white and off-white. |
| `assets/zivo-wordmark-white.svg` | Official wordmark, white. On ink grounds. |
| `assets/zivo-wordmark-red.svg` | Official wordmark, red. Light grounds only, when it is the page's single red element. |
| `assets/zivo-symbol-{ink,white,red}.svg` | The Z. symbol, for square spaces under 120px (favicon, avatar). Never next to the wordmark. |
