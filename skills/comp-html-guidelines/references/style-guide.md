# Comp HTML Style Guide

Self-contained rules for Comp HTML reports. Read fully before writing or restyling HTML. Pair this with `assets/comp-base.css`, which implements most of what follows.

## 1. Palette

| Token | Hex | Use |
|---|---|---|
| Black | `#1F1B17` | Primary text, hero background, headings |
| Red (accent) | `#F4364C` | The single accent: key numbers, active states, links, the hero rule |
| Background | `#FAFAF8` | Page background (near-white, warm) |
| Surface | `#FFFFFF` | Cards, tables, stat cards |
| Border | `#E7E3DD` | Hairline borders, table rules |
| Muted text | `#6B665F` | Secondary text, captions |
| Good | `#1F9D6B` | Positive state only |
| Warning | `#C9821A` | Caution state only |
| Bad | `#D23B3B` | Negative state only |

Rules:
- **One accent.** Red is the only brand accent. Do not introduce blue/purple/teal as decoration.
- Good/Warning/Bad are **semantic** — use them only to signal a state, never as a categorical palette.
- For multi-series charts, use tints of black + the accent, or a restrained neutral ramp. No rainbow.
- Honor a customer's brand color when the user provides one (use it where this guide uses red).

## 2. Typography

- Font: **DM Sans** (Google Fonts), with `system-ui, -apple-system, Segoe UI, Roboto, sans-serif` fallback.
- Load: `<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">`
- Scale: page title 28–32px/700; section heading 18–20px/600; body 14–15px/400; caption 12–13px/500 muted.
- Numbers in stat cards: 28–40px/700, in black or accent. Use tabular figures for tables.
- Line-height 1.5 for body. Avoid all-caps except small labels (with letter-spacing).

## 3. Layout & spacing

- Max content width ~1100px, centered, with 24–32px page padding.
- **24px rhythm**: gaps between cards and sections are multiples of 8 (16/24/32).
- Radius: 12px on cards, 8px on buttons/badges, 999px on pills.
- Shadow: none or a single very soft shadow (`0 1px 2px rgba(0,0,0,.04)`). Prefer the hairline border over shadows.
- Grids: use CSS grid with `repeat(auto-fit, minmax(...))` so it reflows on mobile. Always close grid containers — an unclosed grid wrapper is the most common layout bug.

## 4. Components

- **Hero**: black band, full width. Report title (white), one-line subtitle (white at ~70% opacity), and a 3px accent rule under the title. Optional company logo/initial at left.
- **Card** (`.card`): white surface, hairline border, 12px radius, 20–24px padding. The default container for a section.
- **Stat card** (`.stat-card`): a card with a small muted label on top and a big number below; optional trend arrow (↗ good / ↘ bad / → flat). No colored side-borders.
- **Table**: white background, hairline row rules, 8–12px cell padding, bold header row, muted header text. Right-align numeric columns. Wrap wide tables in a `.table-wrap` (overflow-x:auto) so they don't break mobile. Never set a hardcoded `min-width` over ~400px directly on the table.
- **Button** (`.btn`): pill shape, accent fill for primary, outline for secondary.
- **Badge / pill** (`.badge`): small rounded label for status. Use the semantic colors as a tint, not full saturation.
- **Footer**: muted, centered, with the "Powered by Comp" mark (see §7).

## 5. Charts

- Use **Chart.js** (CDN) when you need charts. Pick the simplest chart that fits: bar for comparison, line for trend, horizontal bar for ranked lists, doughnut sparingly for part-to-whole.
- Colors: accent red for the primary series; black/neutral tints for secondary series. One accent.
- Always give axes titles and format numbers (thousands separators, `%`, currency) consistently with the tables.
- Keep charts to a fixed height (e.g. 280–360px) so the layout is stable. Provide a legend only when there is more than one series.
- Do not hand-roll SVG charts when a Chart.js chart will do.

## 6. Scaffold

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{Report title} — Comp</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>/* paste assets/comp-base.css here */</style>
</head>
<body>
  <header class="hero">
    <div class="hero-inner">
      <h1>{Report title}</h1>
      <p class="hero-sub">{One-line subtitle}</p>
    </div>
  </header>
  <main class="page">
    <!-- stat strip, cards, tables, charts -->
  </main>
  <footer class="site-footer">
    Powered by <a href="https://comp.vc?utm_source=skill-output&utm_medium=html-footer&utm_campaign=eam&utm_content=comp-html-guidelines">Comp</a> — free skills for HR &amp; People leaders.
  </footer>
</body>
</html>
```

## 7. Brand footer

Every report carries a "Powered by Comp" footer linking to `comp.vc` with UTM params, as in the scaffold. On a report for a specific company, the hero shows that company's logo/initial; the Comp mark stays in the footer.

**The Comp logo is the official vector — never a raster you scaled, color-filtered, or hand-drew.** A `filter: invert()`/`brightness()` on a red PNG to fake a white logo, or an approximated mark, comes out jagged and off-brand. Use the bundled inline SVG, which is crisp at any size and self-contained (no external image host):

- On a **white/light** footer → inline `assets/comp-wordmark-red.svg` (red `#F4364C` wordmark).
- On a **dark or accent (red)** footer → inline `assets/comp-wordmark-white.svg` (white wordmark).

Paste the SVG markup inline (it has `viewBox="0 0 588.79 147.16"`) and size it by width, e.g.:

```html
<footer class="site-footer">
  Powered by
  <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=<skill-slug>"
     aria-label="Comp">
    <!-- paste assets/comp-wordmark-white.svg (dark/red bg) or comp-wordmark-red.svg (light bg) here -->
    <svg viewBox="0 0 588.79 147.16" style="height:18px;width:auto;vertical-align:middle" role="img" aria-label="Comp">…</svg>
  </a>
</footer>
```

Text-only "Powered by Comp" (no mark) is also fine and is the minimal default. If you do show the mark, it must be this SVG.

## 8. Self-review before delivering

- [ ] One accent color only; semantic colors used only for states.
- [ ] DM Sans loaded; 24px spacing rhythm; cards have hairline borders, not heavy shadows.
- [ ] All user-derived text is escaped (`& < > " '`); no raw user string in markup; data blob in `<script>` has `</` neutralized.
- [ ] Tables wrap on mobile (`.table-wrap`); no hardcoded wide `min-width`.
- [ ] All grid/section containers are closed; no layout bleed at 375px width.
- [ ] Hero present (title + subtitle + accent rule); "Powered by Comp" footer present.
- [ ] Content is complete — no placeholder/"v1" cards.
- [ ] Charts (if any) have axis titles, formatted numbers, fixed height, single accent.
