# Zivo HTML Style Guide

Self-contained rules for every HTML report, page, dashboard or assessment produced by a Zivo skill. Read it in full before writing or restyling HTML. `assets/zivo-base.css` implements most of what follows; `assets/zivo-tailwind.html` is the drop-in theme for pages built with the Tailwind CDN.

Source: Zivo Brand Guidelines v1.0 (Nov 2026), adapted for data-heavy HR reports. `assets/zivo-example.html` is a finished reference page that applies every rule. When a rule here conflicts with a generic best practice, this guide wins.

## 0. Hard rules (the ones broken most often)

1. **Square corners.** No `border-radius` anywhere, except the small status badge (pill).
2. **No shadows, glows, gradients or outlines.** Separation comes from hairline rules and space.
3. **Four brand colours only:** ink `#1A1A1A`, off-white `#F1F1EA`, white `#FFFFFF`, red `#F4364C`. Status and chart colours come from §1.3 and §1.4, never invented.
4. **Red is rare.** The hero's square start node is red. Beyond it, at most one red highlight per section: the key figure, the chart's highlighted value, or the page's single primary button. Never red body text, never red links, never red on red.
5. **Headlines in the display face, regular weight, sentence case.** Never bold, never all caps, never italic.
6. **Write "Zivo"** in text and **"AI-native"** with a lowercase n. Never type "ZIVO"; the capitalised form exists only as the drawn wordmark.
7. **No emoji, no decorative icons, no stock images.** In interfaces the only glyph is the arrow →.

## 1. Colour

### 1.1 Brand palette

| Token | Hex | Use |
|---|---|---|
| Ink | `#1A1A1A` | Text, headings, hero ground, default buttons, chart data |
| Off-white | `#F1F1EA` | Page background |
| White | `#FFFFFF` | Cards, tables, stat cards |
| Red | `#F4364C` | The hero start node plus at most one highlight per section (hard rule 4). Hover `#E02A40`, pressed `#9E1528` |

### 1.2 Ink tints (interface, tables, charts only)

| Tint | Value | Use |
|---|---|---|
| Ink 80% | `rgba(26,26,26,.8)` | Secondary text |
| Ink 60% | `rgba(26,26,26,.6)` | Captions, muted labels |
| Ink 40% | `rgba(26,26,26,.4)` | Chart baseline |
| Ink 30% | `rgba(26,26,26,.3)` | Header-row rule |
| Ink 20% | `rgba(26,26,26,.2)` | Chart grid |
| Ink 10% | `rgba(26,26,26,.1)` | Card borders, table rules, dividers |
| Ink 5% | `rgba(26,26,26,.05)` | Zebra rows, neutral badge |

Tints are never a brand ground (no grey hero, no grey page).

### 1.3 Status (states only, under 10% of the page)

| State | Fill | Text | Background | Meaning |
|---|---|---|---|---|
| Success | `#12B76A` | `#0B7A43` | `#DDF7EA` | Good, done, within range |
| Warning | `#F69B10` | `#985704` | `#FFF2DA` | Needs attention, not blocking |
| Error | `#D61F35` | `#B3172A` | `#FEE7EA` | Bad, failed, out of range. This is not brand red |
| Info | `#1C7CE5` | `#0B58BB` | `#E7F1FF` | Neutral information, tips |

Use status colours only to signal a state (a badge, a cell flag, a trend arrow). Never as a categorical palette and never in charts.

### 1.4 Chart series (max 6, in this order)

ink `#1A1A1A` → indigo `#4636F2` → aqua `#12C3C9` → orchid `#C24BE6` → citron `#D4E030` → midnight `#1F188C`.

Red `#F4364C` marks the one highlighted value (the bar, point or slice the title is about). A single-series chart is ink with at most one red bar.

### 1.5 Customer brand

On a report about a specific company, the user may give a logo URL and a brand colour. Use their colour only in their logo tile in the hero. Never replace Zivo red with it elsewhere, never fabricate a logo; if none is given, show the company initial in an ink square tile.

## 2. Typography

The brand faces are ABC Arizona Flare (display) and ABC Arizona Sans (text). Their licence does not allow redistribution, so reports use the official fallbacks from Google Fonts: **Marcellus** for Flare and **Source Sans 3** for Sans. The font stacks list Arizona first, so machines that have it installed render the real faces.

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Marcellus&family=Source+Sans+3:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
```

| Style | Face · size / line-height | Tracking | Use |
|---|---|---|---|
| Display | Flare 56 / 54 | −2% | The hero title or the one big number |
| Headline | Flare 32 / 36 | −1% | Section titles |
| Subhead | Flare 22 / 28 | 0 | One line under a headline, card titles |
| Body | Sans 16 / 24 | 0 | Running text |
| Small | Sans 14 / 20 | 0 | Table cells, notes, sources |
| Caption | Sans 12 / 16, capitals | +4% | Labels, header row, table header |

- Hierarchy from size and face, never from weight. Flare is regular only. Sans Bold is allowed for emphasis inside text and for table header labels, never for headlines.
- Left-aligned, ragged right. Never justify. Centre only a single number inside its own box.
- Numbers in tables and stat cards use `font-variant-numeric: tabular-nums`.
- Mobile (under 560px): Display 36/36, Headline 26/30.

## 3. Writing on the page

- Titles state the finding, not the topic: "Mulheres ganham 12% menos em Engenharia", not "Pay gap por área". Chart titles follow the same rule.
- Sentence case everywhere, including buttons, tabs and table headers (the caption style applies capitals by CSS, the source text stays in sentence case).
- Short, direct sentences. Name the number, the mechanism and the consequence.
- Calls to action: a short verb plus one arrow: "Baixar relatório →", "Ver metodologia →".
- No emoji, no exclamation-mark hype, no vague adjectives ("smart", "seamless"). Use "employees" / "colaboradores" for company size in prose.

## 4. Layout

- Page background off-white. Content max width 1120px, centred, side padding 32px (20px on mobile).
- One spacing unit `m = 24px`; gaps are multiples of 8 (8/16/24/32/48).
- Grids with `repeat(auto-fit, minmax(…, 1fr))` so they reflow on mobile. Close every grid wrapper (an unclosed wrapper is the most common layout bug).
- No layout bleed at 375px width. Wrap wide tables in `.table-wrap`; never put a hardcoded `min-width` above ~400px on a table.

## 5. Components

- **Header row** (`.zv-header-row`): at the very top of the hero, up to four captions over a 1px rule, e.g. `Zivo · Pay gap · 2026 · Confidencial`. The first caption is preceded by the 8px square start node (red).
- **Hero** (`.hero`): ink band, white text. Header row, then the Display title (the finding), then one Subhead line at white 70%. Optional customer logo tile (square) on the right. The red start node in the header row is the hero's only red.
- **Card** (`.card`): white, 1px ink-10% border, square, 24px padding. Card title in Subhead.
- **Stat card** (`.stat-card`): caption label, then the number in Flare 40/44, then one sentence of context in Small. At most one stat on the page is red (`.value.accent`), and only when that number is the point. Trend glyphs ↗ ↘ → in status text colours.
- **Big number** (`.big-number`): Flare display number, a 1px rule, and a one-sentence label. One per page.
- **Table**: white, caption-style header row on a 1px ink-30% rule, ink-10% row rules, 10–12px cell padding, numeric columns right-aligned with tabular figures.
- **Button** (`.btn`): square rectangle, Sans, one arrow. Ink fill by default (`.btn`), outline for secondary (`.btn-secondary`), red only for the single primary action on the page (`.btn-primary`).
- **Badge** (`.badge`): the only rounded element (pill). Status background + status text colour from §1.3, or ink 5% for neutral.
- **Overline / list marker** (`.zv-dot`): 8px ink square before a caption; red only for the current or highlighted item.
- **Links**: ink, underlined. Not red.
- **Progress bars and meters**: square, ink fill on an ink-10% track; status colour only when the bar encodes a state.
- **Footer** (`.site-footer`): 1px ink-10% top rule, wordmark bottom-left, "Powered by Zivo · free skills for HR & People leaders" in Small ink 60% to the right (§7).

## 6. Charts

- Use **Chart.js** from a CDN (`https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js`). Pick the simplest chart: bar for comparison, horizontal bar for ranked lists, line for trends. No 3D, no doughnut or pie over three parts.
- Order of parts: title (the finding) · subtitle (what and unit) · highlight (the one value, red) · data (ink, or the §1.4 series) · grid (optional, ink 20%) · baseline (ink 40%, bars start at zero) · source (Small).
- Square everything: `borderRadius: 0` on bars, `pointStyle: 'rect'` on points, `borderWidth: 2` lines. No fills under lines, no gradients.
- Label values directly where you can; show a legend only with two or more series, and then with square markers (`usePointStyle: true, pointStyle: 'rect'`).
- Fixed height (280–360px) so the layout is stable. Format numbers like the tables (thousands separators, `%`, `R$`).
- Default Chart.js setup:

```js
Chart.defaults.font.family = '"ABC Arizona Sans","Source Sans 3",system-ui,sans-serif';
Chart.defaults.font.size = 13;
Chart.defaults.color = 'rgba(26,26,26,.8)';
Chart.defaults.borderColor = 'rgba(26,26,26,.2)';
Chart.defaults.elements.bar.borderRadius = 0;
Chart.defaults.elements.point.pointStyle = 'rect';
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.pointStyle = 'rect';
const ZIVO_SERIES = ['#1A1A1A','#4636F2','#12C3C9','#C24BE6','#D4E030','#1F188C'];
const ZIVO_RED = '#F4364C';
```

## 7. Logo and footer

The Zivo wordmark is a drawn vector. Never retype it in a font, never redraw, stretch, recolour, outline or add effects. Never use a raster logo or an external image host. Inline the bundled SVG:

| File | Use on |
|---|---|
| `assets/zivo-wordmark-ink.svg` | White and off-white grounds (default) |
| `assets/zivo-wordmark-white.svg` | Ink ground (hero, dark footer) |
| `assets/zivo-wordmark-red.svg` | Light grounds only, when the wordmark is the page's single red element |
| `assets/zivo-symbol-*.svg` | Square or narrow spaces under 120px wide (favicon, avatar). Never next to the wordmark |

- Wordmark sits on a margin, never floating. Default bottom-left in the footer; top-left for document headers. Minimum height 20px on screen, clear space of one letter height on every side.
- The wordmark SVG has `viewBox="1.0000 0.4375 273.6250 64.9800"`; size it by height (`height:20px;width:auto`).
- Every report ends with the footer below. The UTM `utm_content` is the calling skill's slug.

```html
<footer class="site-footer">
  <a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=<skill-slug>" aria-label="Zivo">
    <!-- paste assets/zivo-wordmark-ink.svg here, with role="img" aria-label="Zivo" -->
  </a>
  <span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer>
```

A text-only "Powered by Zivo" line linking to `zivo.ai` is the minimal fallback when inlining the SVG is not possible (for example, a Markdown answer).

## 8. Scaffold

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{Report title} · Zivo</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Marcellus&family=Source+Sans+3:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
  <style>/* paste assets/zivo-base.css here */</style>
</head>
<body>
  <header class="hero">
    <div class="hero-inner">
      <div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>{Topic}</span><span>{Period}</span></div>
      <h1>{The finding, in sentence case}</h1>
      <p class="hero-sub">{One line: what was analysed, scope, unit}</p>
    </div>
  </header>
  <main class="page">
    <!-- stat strip, cards, tables, charts -->
  </main>
  <footer class="site-footer">…see §7…</footer>
</body>
</html>
```

### Tailwind pages

Pages built with the Tailwind CDN paste `assets/zivo-tailwind.html` right after the Tailwind `<script>` tag. It loads the fonts, maps the Tailwind theme to Zivo (square radii, no shadows, ink/red/off-white tokens, status colours, the font families) and adds the base components above. With it in place, use `bg-zv-off`, `text-zv-ink`, `bg-zv-ink`, `text-zv-red`, `border-zv-line`, `font-display`, `font-sans`. Do not use Tailwind's default palettes (`slate`, `gray`, `rose`, `blue`, `emerald`…) or `rounded-*`, `shadow-*`, `bg-gradient-*` classes: the theme neutralises radii and shadows, but colours and gradients must be removed from the markup.

## 9. Self-review before delivering

- [ ] Only ink, off-white, white and red, plus status colours for states and the §1.4 series in charts.
- [ ] Red only on the hero start node and at most one highlight per section. No red text, no red links.
- [ ] Square corners everywhere except status badges. No shadows, gradients or glows.
- [ ] Headlines in Marcellus/Arizona Flare, regular, sentence case; text in Source Sans 3/Arizona Sans; nothing justified.
- [ ] Titles state findings. No emoji. "Zivo" and "AI-native" spelled correctly.
- [ ] Wordmark is the inline SVG, on a margin (footer bottom-left); no raster logo, no external image host.
- [ ] All user-derived text is escaped (`& < > " '`); a data blob in `<script>` has `</` neutralised.
- [ ] Tables wrap on mobile; no layout bleed at 375px; every grid closed.
- [ ] Charts: square bars and points, ink 20% grid, ink 40% baseline from zero, one red highlight, fixed height.
- [ ] Content is complete: no placeholder or "v1" cards.
