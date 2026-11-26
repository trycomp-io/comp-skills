#!/usr/bin/env python3
"""
dei_funnel.py — Representatividade ao longo do ciclo de vida (além de pay).
Compara o mix demográfico em cada estágio (headcount geral, liderança,
contratações, promoções, saídas) pra identificar onde a representatividade
vaza. Regra de confidencialidade: células com menos de 3 pessoas são omitidas.

Inputs:
  - Roster CSV (atual): name, level (mínimo), + recortes demográficos
    (gender, race/ethnicity, age_band...). Opcional area.
  - Events CSV (opcional): type (hire/promotion/exit), date (opt), + os mesmos
    recortes demográficos.

Output: HTML com representatividade por estágio (barras empilhadas), pontos de
vazamento, gap de liderança, tabelas de taxa.

Uso:
    python3 dei_funnel.py --roster roster.csv
    python3 dei_funnel.py --roster roster.csv --events events.csv --dimension gender
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "representation-dei-funnel"
SKILL_VERSION = "1.0.0"

MIN_CELL = 3  # confidencialidade: grupos com <3 pessoas numa célula são omitidos

NAME_ALIASES = ["name", "nome", "colaborador", "employee", "candidate"]
LEVEL_ALIASES = ["level", "nivel", "nível", "senioridade", "seniority", "grade", "job_level", "cargo_level"]
AREA_ALIASES = ["area", "área", "departamento", "department", "diretoria"]
TYPE_ALIASES = ["type", "tipo", "event_type", "evento"]
DATE_ALIASES = ["date", "data", "event_date"]
# recortes demográficos reconhecidos (chave canônica -> aliases)
DIM_ALIASES = {
    "gender":    ["gender", "genero", "gênero", "sexo", "sex"],
    "race":      ["race", "raca", "raça", "ethnicity", "etnia", "race_ethnicity", "cor", "raca_cor"],
    "age_band":  ["age_band", "faixa_etaria", "faixa_etária", "idade_faixa", "age_group", "geracao", "geração"],
    "pcd":       ["pcd", "disability", "deficiencia", "deficiência"],
    "lgbtqia":   ["lgbtqia", "lgbt", "orientacao", "orientação"],
}

# níveis considerados liderança por padrão (heurística por palavra-chave)
LEADER_KEYWORDS = ["lead", "líder", "lider", "manager", "gerente", "head", "diretor", "director",
                   "vp", "c-level", "cxo", "ceo", "cto", "cfo", "chro", "executive", "executivo",
                   "senior_manager", "principal", "staff", "l5", "l6", "l7", "l8"]


def _esc(v):
    import html
    return html.escape(str(v), quote=True) if v is not None else ""


def _norm(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii").strip().lower().replace(" ", "_")


def detect_one(headers, aliases):
    h = {_norm(x): x for x in headers}
    for cand in aliases:
        if _norm(cand) in h:
            return h[_norm(cand)]
    return None


def detect_dimensions(headers):
    found = {}
    for canon, aliases in DIM_ALIASES.items():
        col = detect_one(headers, aliases)
        if col:
            found[canon] = col
    return found


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def is_leader(level):
    n = _norm(level)
    return any(k in n for k in LEADER_KEYWORDS)


def _val(row, col):
    v = (row.get(col) or "").strip() if col else ""
    return v or None


def counts_by_group(rows, col):
    """Conta pessoas por valor do recorte. Ignora vazios."""
    c = defaultdict(int)
    for r in rows:
        v = _val(r, col)
        if v:
            c[v] += 1
    return c


def apply_confidentiality(raw_counts):
    """Retorna (visiveis, suprimidos_total). Grupos com <MIN_CELL viram suprimidos."""
    visible = {g: n for g, n in raw_counts.items() if n >= MIN_CELL}
    suppressed = sum(n for g, n in raw_counts.items() if n < MIN_CELL)
    return visible, suppressed


def mix_pct(visible):
    total = sum(visible.values())
    if not total:
        return {}, 0
    return {g: round(n / total * 100, 1) for g, n in visible.items()}, total


def analyze(roster, cols, events, ecols, dim_col, dim_label):
    leaders = [r for r in roster if cols.get("level") and is_leader(_val(r, cols["level"]) or "")]

    hires = [e for e in (events or []) if _norm(_val(e, ecols.get("type")) or "") in ("hire", "contratacao", "contratação", "admissao", "admissão")]
    promos = [e for e in (events or []) if _norm(_val(e, ecols.get("type")) or "") in ("promotion", "promocao", "promoção", "promo")]
    exits = [e for e in (events or []) if _norm(_val(e, ecols.get("type")) or "") in ("exit", "saida", "saída", "desligamento", "termination")]

    stages = []
    stage_defs = [
        ("Headcount geral", roster, cols.get(dim_col)),
        ("Liderança", leaders, cols.get(dim_col)),
        ("Contratações", hires, ecols.get(dim_col)),
        ("Promoções", promos, ecols.get(dim_col)),
        ("Saídas", exits, ecols.get(dim_col)),
    ]
    for label, rows, col in stage_defs:
        if not rows or not col:
            stages.append({"stage": label, "available": False, "n": 0, "mix": {}, "counts": {}, "suppressed": 0})
            continue
        raw = counts_by_group(rows, col)
        visible, suppressed = apply_confidentiality(raw)
        pct, total = mix_pct(visible)
        stages.append({
            "stage": label, "available": True, "n": len(rows),
            "mix": pct, "counts": visible, "suppressed": suppressed, "shown_total": total,
        })

    # universo de grupos visíveis (em qualquer estágio)
    groups = sorted({g for s in stages for g in s["mix"].keys()})

    overall = next((s for s in stages if s["stage"] == "Headcount geral"), None)
    leadership = next((s for s in stages if s["stage"] == "Liderança"), None)

    # gap de liderança vs geral, por grupo
    leadership_gap = []
    if overall and leadership and leadership["available"]:
        for g in groups:
            ov = overall["mix"].get(g)
            ld = leadership["mix"].get(g)
            if ov is None:
                continue
            gap = round((ld if ld is not None else 0) - ov, 1)
            leadership_gap.append({"group": g, "overall_pct": ov, "leadership_pct": ld, "gap": gap})
        leadership_gap.sort(key=lambda x: x["gap"])

    # vazamentos: compara contratações vs geral vs promoções vs saídas por grupo
    leaks = []
    hires_s = next((s for s in stages if s["stage"] == "Contratações"), None)
    promos_s = next((s for s in stages if s["stage"] == "Promoções"), None)
    exits_s = next((s for s in stages if s["stage"] == "Saídas"), None)
    for g in groups:
        ov = overall["mix"].get(g) if overall else None
        if ov is None:
            continue
        notes = []
        if hires_s and hires_s["available"] and g in hires_s["mix"]:
            d = round(hires_s["mix"][g] - ov, 1)
            if d <= -5:
                notes.append(f"sub-representado nas contratações ({hires_s['mix'][g]}% vs {ov}% geral)")
        if promos_s and promos_s["available"]:
            pp = promos_s["mix"].get(g, 0 if promos_s["shown_total"] else None)
            if pp is not None and pp - ov <= -5:
                notes.append(f"sub-representado nas promoções ({pp}% vs {ov}% geral)")
        if exits_s and exits_s["available"] and g in exits_s["mix"]:
            d = round(exits_s["mix"][g] - ov, 1)
            if d >= 5:
                notes.append(f"sobre-representado nas saídas ({exits_s['mix'][g]}% vs {ov}% geral)")
        if notes:
            leaks.append({"group": g, "notes": notes})

    # taxas de promoção e saída por grupo (sobre headcount geral visível)
    rates = []
    if overall:
        base = overall["counts"]
        for g in groups:
            hc = base.get(g)
            if not hc:
                continue
            promo_n = promos_s["counts"].get(g) if promos_s and promos_s["available"] else None
            exit_n = exits_s["counts"].get(g) if exits_s and exits_s["available"] else None
            rates.append({
                "group": g, "hc": hc,
                "promo_rate": round(promo_n / hc * 100, 1) if promo_n is not None else None,
                "exit_rate": round(exit_n / hc * 100, 1) if exit_n is not None else None,
            })

    insights = []
    if not overall or not overall["available"]:
        insights.append(f"Não foi possível ler o recorte '{_esc(dim_label)}' no roster — verifique a coluna.")
    else:
        if leadership_gap:
            worst = leadership_gap[0]
            if worst["gap"] <= -5:
                insights.append(f"Grupo <strong>{_esc(worst['group'])}</strong> tem gap de liderança de <strong>{worst['gap']} p.p.</strong> ({worst['overall_pct']}% geral vs {worst['leadership_pct'] or 0}% na liderança).")
        if leaks:
            insights.append(f"<strong>{len(leaks)}</strong> ponto(s) de vazamento de representatividade identificado(s) (contratação, promoção ou saída).")
        n_supp = sum(1 for s in stages if s["suppressed"] > 0)
        if n_supp:
            insights.append(f"Grupos com menos de {MIN_CELL} pessoas numa célula foram omitidos por confidencialidade (em {n_supp} estágio(s)).")
        if not events:
            insights.append("Sem CSV de eventos: análise limitada a headcount e liderança. Adicione contratações/promoções/saídas pra ver o funil completo.")

    return {
        "summary": {
            "dimension": dim_label,
            "roster_n": len(roster),
            "leaders_n": len(leaders),
            "has_events": bool(events),
            "groups": groups,
        },
        "stages": stages,
        "leadership_gap": leadership_gap,
        "leaks": leaks,
        "rates": rates,
        "insights": insights,
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Representation DEI Funnel · Zivo</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<!-- Zivo theme for pages built with the Tailwind CDN.
     Paste right after <script src="https://cdn.tailwindcss.com/3.4.16"></script>.
     Square radii, no shadows, Zivo tokens and fonts. See references/style-guide.md §8. -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Marcellus&family=Source+Sans+3:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<script>
tailwind.config = {
  theme: {
    borderRadius: { none: '0', sm: '0', DEFAULT: '0', md: '0', lg: '0', xl: '0', '2xl': '0', '3xl': '0', full: '9999px' },
    boxShadow: { sm: 'none', DEFAULT: 'none', md: 'none', lg: 'none', xl: 'none', '2xl': 'none', inner: 'none', none: 'none' },
    fontFamily: {
      display: ['"ABC Arizona Flare"', 'Marcellus', 'Georgia', 'serif'],
      sans: ['"ABC Arizona Sans"', '"Source Sans 3"', 'system-ui', 'sans-serif'],
    },
    extend: {
      colors: {
        zv: {
          ink: '#1A1A1A', off: '#F1F1EA', white: '#FFFFFF',
          red: '#F4364C', 'red-hover': '#E02A40', 'red-pressed': '#9E1528',
          ink80: 'rgba(26,26,26,.8)', ink60: 'rgba(26,26,26,.6)', ink40: 'rgba(26,26,26,.4)',
          ink30: 'rgba(26,26,26,.3)', ink20: 'rgba(26,26,26,.2)', line: 'rgba(26,26,26,.1)', ink05: 'rgba(26,26,26,.05)',
          success: '#0B7A43', 'success-bg': '#DDF7EA', 'success-fill': '#12B76A',
          warning: '#985704', 'warning-bg': '#FFF2DA', 'warning-fill': '#F69B10',
          error: '#B3172A', 'error-bg': '#FEE7EA', 'error-fill': '#D61F35',
          info: '#0B58BB', 'info-bg': '#E7F1FF', 'info-fill': '#1C7CE5',
          indigo: '#4636F2', aqua: '#12C3C9', orchid: '#C24BE6', citron: '#D4E030', midnight: '#1F188C',
        },
      },
    },
  },
};
</script>
<style>
  body { font-family: "ABC Arizona Sans", "Source Sans 3", system-ui, sans-serif; background: #F1F1EA; color: #1A1A1A; }
  h1, h2, h3, h4, .font-display { font-family: "ABC Arizona Flare", Marcellus, Georgia, serif; font-weight: 400 !important; font-style: normal; text-transform: none; }
  h1 { letter-spacing: -0.02em; }
  h2 { letter-spacing: -0.01em; }
  a { text-underline-offset: 2px; }
  .zv-dot { display: inline-block; width: 8px; height: 8px; background: currentColor; margin-right: 8px; vertical-align: 1px; }
  .zv-dot--red { background: #F4364C; }
  .zv-caption { font-size: 12px; line-height: 16px; text-transform: uppercase; letter-spacing: .04em; }
  .zv-wordmark { display: inline-flex; line-height: 0; }
  .zv-wordmark svg { height: 20px; width: auto; }
  .tabular { font-variant-numeric: tabular-nums; }
</style>
<style>
  *,::before,::after{border-radius:0;box-shadow:none}
  body{margin:0;background:#F1F1EA;color:#1A1A1A;font-size:16px;line-height:1.5;-webkit-font-smoothing:antialiased}
  .hero{background:#1A1A1A;color:#FFFFFF;padding:32px 0 48px}
  .hero-inner{max-width:1120px;margin:0 auto;padding:0 32px}
  .zv-header-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:24px;padding-bottom:10px;margin-bottom:40px;border-bottom:1px solid rgba(255,255,255,.3);color:rgba(255,255,255,.8);font-size:12px;line-height:16px;text-transform:uppercase;letter-spacing:.04em}
  .hero h1{font-size:56px;line-height:54px;color:#FFFFFF;max-width:22ch;margin:0}
  .hero-sub{margin:16px 0 0;color:rgba(255,255,255,.7);font-family:"ABC Arizona Flare",Marcellus,Georgia,serif;font-size:22px;line-height:28px;max-width:60ch}
  .hero-sub a{color:#FFFFFF;text-decoration:underline;text-underline-offset:2px}
  .page{max-width:1120px;margin:0 auto;padding:48px 32px}
  .page a{color:#1A1A1A;text-decoration:underline;text-underline-offset:2px}
  .card{background:#FFFFFF;border:1px solid rgba(26,26,26,.1);padding:24px;margin-bottom:24px;min-width:0}
  .card h2{font-size:22px;line-height:28px;margin-bottom:16px}
  .stat{font-family:"ABC Arizona Flare",Marcellus,Georgia,serif;font-size:40px;line-height:44px;margin-top:8px;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
  .stat.accent{color:#F4364C}
  .stat-label{font-size:12px;line-height:16px;text-transform:uppercase;letter-spacing:.04em;color:rgba(26,26,26,.6)}
  .page table{width:100%;border-collapse:collapse;font-size:14px;line-height:20px;background:#FFFFFF}
  .page th{text-align:left;font-weight:700;font-size:12px;line-height:16px;text-transform:uppercase;letter-spacing:.04em;color:rgba(26,26,26,.8);background:#FFFFFF;border-bottom:1px solid rgba(26,26,26,.3);padding:10px 12px}
  .page td{padding:10px 12px;border-bottom:1px solid rgba(26,26,26,.1);vertical-align:top;font-variant-numeric:tabular-nums}
  .page tbody tr:last-child td{border-bottom:none}
  .badge,.pill{display:inline-block;white-space:nowrap;padding:2px 10px;border-radius:999px;font-family:"ABC Arizona Sans","Source Sans 3",system-ui,sans-serif;font-size:12px;line-height:18px;font-weight:700;background:rgba(26,26,26,.05);color:#1A1A1A}
  .badge-good{background:#DDF7EA;color:#0B7A43}.badge-warn{background:#FFF2DA;color:#985704}
  .badge-bad{background:#FEE7EA;color:#B3172A}.badge-info{background:#E7F1FF;color:#0B58BB}
  .st-good{color:#0B7A43;font-weight:700}.st-warn{color:#985704;font-weight:700}.st-bad{color:#B3172A;font-weight:700}
  .zv-list li{display:flex;align-items:flex-start}
  .zv-list .zv-dot{flex:none;margin-top:8px}
  .site-footer{max-width:1120px;margin:0 auto;padding:24px 32px 40px;display:flex;align-items:center;gap:24px;flex-wrap:wrap;border-top:1px solid rgba(26,26,26,.1);font-size:14px;line-height:20px;color:rgba(26,26,26,.6)}
  .site-footer a{color:inherit}
  @media (max-width:560px){
    .hero-inner,.page,.site-footer{padding-left:20px;padding-right:20px}
    .hero h1{font-size:36px;line-height:36px}
    .zv-header-row{grid-template-columns:repeat(2,minmax(0,1fr));row-gap:8px}
    .stat{font-size:32px;line-height:36px}
    .card{padding:16px}
    .page th,.page td{padding:8px 6px}
  }
  .bar{display:flex;height:32px;overflow:hidden;font-size:12px;font-weight:700;background:rgba(26,26,26,.05)}
  .seg{display:flex;align-items:center;justify-content:center;min-width:24px}
  .leak{border-top:1px solid #1A1A1A;padding:12px 0 4px;margin-bottom:8px}
  .legend{display:inline-flex;align-items:center;gap:6px;font-size:13px;margin-right:16px}
  .swatch{width:12px;height:12px;display:inline-block}
</style></head>
<body>
<header class="hero"><div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>Representatividade</span><span><span id="generated"></span></span><span>Confidencial</span></div>
<h1>Representatividade ao longo do ciclo</h1>
<p class="hero-sub">Mix por grupo em cada estágio, da contratação à liderança, com os pontos de vazamento.</p>
</div></header>
<main class="page">

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
<div class="card"><div class="stat-label">Recorte</div><div class="stat" id="s-dim"></div></div>
<div class="card"><div class="stat-label">Headcount</div><div class="stat" id="s-hc"></div></div>
<div class="card"><div class="stat-label">Liderança</div><div class="stat" id="s-lead"></div></div>
<div class="card"><div class="stat-label">Grupos</div><div class="stat" id="s-groups"></div></div>
</div>

<div class="card">
<h2 style="margin-bottom:8px">Mix por estágio</h2>
<div id="legend" class="mb-4"></div>
<div id="stages" class="space-y-4"></div>
<p class="text-xs text-zv-ink60 mt-4">Células com menos de 3 pessoas são omitidas por confidencialidade; percentuais são sobre o total visível de cada estágio.</p>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2>Insights</h2>
<ul class="space-y-2 zv-list" id="insights-list"></ul>
</div>

<div class="card" id="leaks-card" style="display:none;">
<h2>Pontos de vazamento</h2>
<div id="leaks"></div>
</div>

<div class="card" id="gap-card" style="display:none;">
<h2>Gap de liderança vs geral</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Grupo</th><th>% Geral</th><th>% Liderança</th><th>Gap (p.p.)</th></tr></thead><tbody id="gap-tbody"></tbody></table></div>
</div>

<div class="card" id="rates-card" style="display:none;">
<h2>Taxas por grupo</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Grupo</th><th>HC</th><th>Taxa de promoção</th><th>Taxa de saída</th></tr></thead><tbody id="rates-tbody"></tbody></table></div>
</div>

</main>
<footer class="site-footer">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=representation-dei-funnel" aria-label="Zivo"><svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg></a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });
// Zivo chart series (style guide 1.4), then ink tints for groups beyond six.
const PALETTE = ['#1A1A1A','#4636F2','#12C3C9','#C24BE6','#D4E030','#1F188C','rgba(26,26,26,.6)','rgba(26,26,26,.35)'];
const LIGHT = ['#12C3C9','#D4E030','rgba(26,26,26,.35)'];
const txtFor = c => LIGHT.includes(c) ? '#1A1A1A' : '#FFFFFF';
const colorFor = {};
DATA.summary.groups.forEach((g,i) => colorFor[g] = PALETTE[i % PALETTE.length]);

document.getElementById('s-dim').textContent = DATA.summary.dimension;
document.getElementById('s-hc').textContent = DATA.summary.roster_n;
document.getElementById('s-lead').textContent = DATA.summary.leaders_n;
document.getElementById('s-groups').textContent = DATA.summary.groups.length;

document.getElementById('legend').innerHTML = DATA.summary.groups.map(g =>
  `<span class="legend"><span class="swatch" style="background:${colorFor[g]}"></span>${esc(g)}</span>`).join('');

document.getElementById('stages').innerHTML = DATA.stages.map(s => {
  if (!s.available) return `<div><div class="text-sm font-semibold">${esc(s.stage)}</div><div class="text-xs text-zv-ink60">sem dados</div></div>`;
  const segs = DATA.summary.groups.filter(g => s.mix[g] !== undefined).map(g =>
    `<div class="seg" style="width:${s.mix[g]}%;background:${colorFor[g]};color:${txtFor(colorFor[g])}" title="${esc(g)}: ${s.mix[g]}%">${s.mix[g] >= 8 ? s.mix[g]+'%' : ''}</div>`).join('');
  const supp = s.suppressed > 0 ? ` <span class="text-xs text-zv-ink60">(+${s.suppressed} omitidos)</span>` : '';
  return `<div><div class="text-sm font-semibold mb-1">${esc(s.stage)} <span class="text-zv-ink60 font-normal">n=${s.n}</span>${supp}</div><div class="bar">${segs}</div></div>`;
}).join('');

if (DATA.insights.length > 0) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li class="flex items-start"><i class="zv-dot"></i><span>${i}</span></li>`).join('');
}

if (DATA.leaks.length > 0) {
  document.getElementById('leaks-card').style.display = '';
  document.getElementById('leaks').innerHTML = DATA.leaks.map(l =>
    `<div class="leak"><strong>${esc(l.group)}</strong><ul class="list-disc ml-5 mt-1 text-sm text-zv-ink80">${l.notes.map(n => `<li>${esc(n)}</li>`).join('')}</ul></div>`).join('');
}

if (DATA.leadership_gap.length > 0) {
  document.getElementById('gap-card').style.display = '';
  document.getElementById('gap-tbody').innerHTML = DATA.leadership_gap.map(r =>
    `<tr><td><strong>${esc(r.group)}</strong></td><td>${r.overall_pct}%</td><td>${r.leadership_pct === null ? '—' : r.leadership_pct+'%'}</td><td class="${r.gap < 0 ? 'st-bad' : 'st-good'}">${r.gap > 0 ? '+' : ''}${r.gap}</td></tr>`).join('');
}

if (DATA.rates.length > 0) {
  document.getElementById('rates-card').style.display = '';
  document.getElementById('rates-tbody').innerHTML = DATA.rates.map(r =>
    `<tr><td><strong>${esc(r.group)}</strong></td><td>${r.hc}</td><td>${r.promo_rate === null ? '—' : r.promo_rate+'%'}</td><td>${r.exit_rate === null ? '—' : r.exit_rate+'%'}</td></tr>`).join('');
}
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Funil de representatividade (DEI) ao longo do ciclo.")
    p.add_argument("--roster", type=Path, required=True)
    p.add_argument("--events", type=Path, help="CSV opcional (type=hire/promotion/exit + recortes demográficos)")
    p.add_argument("--dimension", help="Recorte a analisar: gender, race, age_band, pcd, lgbtqia. Default: primeiro detectado.")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    headers_r, roster = load_csv(args.roster)
    cols = {
        "name": detect_one(headers_r, NAME_ALIASES),
        "level": detect_one(headers_r, LEVEL_ALIASES),
        "area": detect_one(headers_r, AREA_ALIASES),
    }
    cols.update(detect_dimensions(headers_r))
    dims = [d for d in DIM_ALIASES if d in cols]
    if not dims:
        sys.exit("Nenhum recorte demográfico detectado no roster (gender, race, age_band...). Verifique colunas.")

    events, ecols = [], {}
    if args.events:
        headers_e, events = load_csv(args.events)
        ecols = {"type": detect_one(headers_e, TYPE_ALIASES), "date": detect_one(headers_e, DATE_ALIASES)}
        ecols.update(detect_dimensions(headers_e))

    dim = args.dimension if (args.dimension and args.dimension in cols) else dims[0]
    print(f"Roster: {len(roster)} | Events: {len(events)} | recortes detectados: {', '.join(dims)} | analisando: {dim}")

    data = analyze(roster, cols, events, ecols, dim, dim)
    out = args.output or Path.cwd() / f"dei-funnel-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    print(f"  recorte '{dim}' | {len(data['summary']['groups'])} grupos visíveis | {len(data['leaks'])} ponto(s) de vazamento")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=representation-dei-funnel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
