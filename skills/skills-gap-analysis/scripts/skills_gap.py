#!/usr/bin/env python3
"""
skills_gap.py — Analisa lacunas de capacidade da força de trabalho contra um
conjunto de capacidades-alvo. Calcula cobertura por skill, magnitude do gap,
prioridade (criticidade × gap) e recomendação build/buy/borrow.

Inputs:
  - Inventory CSV: person, skill, proficiency (1-5)
  - Target CSV: skill, required_proficiency (1-5), criticality (1-5), headcount_needed

Output: HTML executivo com heatmap (skill × criticidade), lista priorizada de
gaps com build/buy/borrow, e resumo de implicações de hiring/training.

Uso:
    python3 skills_gap.py --inventory inv.csv --target target.csv
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

SKILL_NAME = "skills-gap-analysis"
SKILL_VERSION = "1.0.0"


INV_ALIASES = {
    "person":      ["person", "pessoa", "colaborador", "name", "nome"],
    "skill":       ["skill", "competencia", "competência", "habilidade"],
    "proficiency": ["proficiency", "proficiencia", "proficiência", "nivel", "nível", "level", "score"],
}
TARGET_ALIASES = {
    "skill":                ["skill", "competencia", "competência", "habilidade"],
    "required_proficiency": ["required_proficiency", "required", "proficiencia_requerida", "nivel_requerido", "required_level"],
    "criticality":          ["criticality", "criticidade", "importancia", "importância", "priority"],
    "headcount_needed":     ["headcount_needed", "headcount", "hc", "hc_needed", "vagas", "necessario", "necessário"],
}


def _esc(v):
    import html
    return html.escape(str(v), quote=True) if v is not None else ""


def _norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").strip().lower().replace(" ", "_")


def auto_detect(headers, aliases, key):
    h = {_norm(x): x for x in headers}
    for cand in aliases[key]:
        if _norm(cand) in h:
            return h[_norm(cand)]
    return None


def _f(v):
    if v is None or v == "":
        return None
    s = str(v).strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def recommend(gap, criticality, coverage_ratio):
    """build / buy / borrow.
    BUY: gap grande + alta criticidade (precisa de capacidade nova permanente).
    BORROW: criticidade baixa/média (niche ou temporário) — contractor/parceiro.
    BUILD: gap moderado e já existe base interna (cobertura parcial) — treinar.
    """
    if criticality >= 4 and coverage_ratio < 0.5:
        return ("BUY", "Gap grande em capacidade crítica — contratar é o caminho mais rápido e confiável pra fechar.")
    if coverage_ratio >= 0.5 and gap > 0:
        return ("BUILD", "Já existe base interna parcial — treinar/desenvolver é mais barato e retém conhecimento.")
    if criticality <= 2:
        return ("BORROW", "Capacidade de baixa criticidade ou pontual — contractor/parceiro evita custo fixo.")
    return ("BUILD", "Gap moderado em capacidade relevante — desenvolver internamente com plano de treino.")


def analyze(inventory, target, cols_inv, cols_tgt):
    # cobertura por skill: pessoas com proficiência >= required
    skill_people = defaultdict(list)  # skill -> [(person, prof)]
    for row in inventory:
        skill = (row.get(cols_inv["skill"]) or "").strip()
        prof = _f(row.get(cols_inv["proficiency"]))
        if not skill or prof is None:
            continue
        person = (row.get(cols_inv.get("person") or "") or "—").strip()
        skill_people[_norm(skill)].append({"display": skill, "person": person, "prof": prof})

    gaps = []
    for trow in target:
        skill = (trow.get(cols_tgt["skill"]) or "").strip()
        req = _f(trow.get(cols_tgt["required_proficiency"]))
        crit = _f(trow.get(cols_tgt.get("criticality") or "")) or 3.0
        hc = _f(trow.get(cols_tgt["headcount_needed"])) or 1.0
        if not skill or req is None:
            continue
        crit = max(1.0, min(5.0, crit))
        hc = max(1.0, hc)
        people = skill_people.get(_norm(skill), [])
        covered = sum(1 for p in people if p["prof"] >= req)
        gap = max(0.0, hc - covered)
        coverage_ratio = round(min(1.0, covered / hc), 3) if hc else 0.0
        # prioridade = criticidade × magnitude do gap (normalizado pelo hc)
        gap_magnitude = gap / hc if hc else 0.0
        priority = round(crit * gap_magnitude, 3)
        rec, rationale = recommend(gap, crit, coverage_ratio)
        gaps.append({
            "skill": skill,
            "required": req,
            "criticality": int(crit),
            "headcount_needed": int(hc),
            "covered": covered,
            "gap": int(gap),
            "coverage_pct": round(coverage_ratio * 100, 1),
            "priority": priority,
            "recommendation": rec,
            "rationale": rationale,
        })

    gaps.sort(key=lambda g: (-g["priority"], -g["criticality"], -g["gap"]))

    # heatmap: skill (linha) × criticidade (coluna), valor = gap
    heatmap = [{"skill": g["skill"], "criticality": g["criticality"], "gap": g["gap"],
                "coverage_pct": g["coverage_pct"]} for g in gaps]

    # resumo build/buy/borrow
    bbb = defaultdict(lambda: {"count": 0, "hc": 0})
    total_gap_hc = 0
    for g in gaps:
        if g["gap"] > 0:
            bbb[g["recommendation"]]["count"] += 1
            bbb[g["recommendation"]]["hc"] += g["gap"]
            total_gap_hc += g["gap"]

    insights = []
    open_gaps = [g for g in gaps if g["gap"] > 0]
    if not open_gaps:
        insights.append("Nenhum gap aberto — todas as capacidades-alvo estão cobertas no nível requerido.")
    else:
        buy_hc = bbb.get("BUY", {}).get("hc", 0)
        build_hc = bbb.get("BUILD", {}).get("hc", 0)
        borrow_hc = bbb.get("BORROW", {}).get("hc", 0)
        insights.append(f"<strong>{len(open_gaps)} skill(s)</strong> com gap aberto, somando <strong>{total_gap_hc} posição(ões)</strong> de capacidade a fechar.")
        if buy_hc:
            insights.append(f"<strong>BUY</strong>: ~{buy_hc} contratação(ões) em capacidades críticas com cobertura baixa — priorize requisições.")
        if build_hc:
            insights.append(f"<strong>BUILD</strong>: ~{build_hc} posição(ões) cobríveis via treino/desenvolvimento interno — base parcial já existe.")
        if borrow_hc:
            insights.append(f"<strong>BORROW</strong>: ~{borrow_hc} posição(ões) endereçáveis com contractor/parceiro (baixa criticidade ou pontual).")
        top = open_gaps[0]
        insights.append(f"Maior prioridade: <strong>{_esc(top['skill'])}</strong> (criticidade {top['criticality']}, gap {top['gap']}) → recomendação {top['recommendation']}.")

    return {
        "summary": {
            "skills_evaluated": len(gaps),
            "open_gaps": len(open_gaps),
            "total_gap_hc": total_gap_hc,
            "people_in_inventory": len({(r.get(cols_inv.get("person") or "") or "").strip() for r in inventory if (r.get(cols_inv.get("person") or "") or "").strip()}),
        },
        "gaps": gaps,
        "heatmap": heatmap,
        "build_buy_borrow": {k: bbb[k] for k in ("BUILD", "BUY", "BORROW") if k in bbb},
        "insights": insights,
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Skills Gap Analysis · Zivo</title>
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
  .hm-cell{padding:8px;text-align:center;font-weight:700;font-size:13px;line-height:16px}
  .bbb-tile{background:#FFFFFF;border:1px solid rgba(26,26,26,.1);padding:20px}
</style></head>
<body>
<header class="hero"><div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>Skills gap</span><span><span id="generated"></span></span><span>Confidencial</span></div>
<h1>Lacunas de capacidade: build, buy ou borrow</h1>
<p class="hero-sub">Cobertura das skills críticas contra o inventário atual, com a ação recomendada pra cada lacuna.</p>
</div></header>
<main class="page">

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
<div class="card"><div class="stat-label">Skills avaliadas</div><div class="stat" id="s-eval"></div></div>
<div class="card"><div class="stat-label">Gaps abertos</div><div class="stat accent" id="s-open"></div></div>
<div class="card"><div class="stat-label">Posições a fechar</div><div class="stat" id="s-hc"></div></div>
<div class="card"><div class="stat-label">Pessoas no inventário</div><div class="stat" id="s-people"></div></div>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2>Insights</h2>
<ul class="space-y-2 zv-list" id="insights-list"></ul>
</div>

<div class="card">
<h2 style="margin-bottom:4px">Heatmap: skill × criticidade</h2>
<p class="text-xs text-zv-ink60 mb-4">Cor = tamanho do gap (vermelho = gap maior, verde = gap menor). Coluna = criticidade (1-5).</p>
<div class="overflow-x-auto"><table><thead><tr><th>Skill</th><th>Crit 1</th><th>Crit 2</th><th>Crit 3</th><th>Crit 4</th><th>Crit 5</th></tr></thead><tbody id="hm-tbody"></tbody></table></div>
</div>

<div class="card">
<h2>Gaps priorizados</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Skill</th><th>Prof. req.</th><th>Crit.</th><th>HC alvo</th><th>Cobertos</th><th>Gap</th><th>Cobertura</th><th>Prioridade</th><th>Ação</th><th>Rationale</th></tr></thead><tbody id="gap-tbody"></tbody></table></div>
</div>

<div class="card">
<h2>Implicações de hiring / training</h2>
<div class="grid sm:grid-cols-3 gap-3" id="bbb"></div>
</div>

</main>
<footer class="site-footer">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=skills-gap-analysis" aria-label="Zivo"><svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg></a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });

document.getElementById('s-eval').textContent = DATA.summary.skills_evaluated;
document.getElementById('s-open').textContent = DATA.summary.open_gaps;
document.getElementById('s-hc').textContent = DATA.summary.total_gap_hc;
document.getElementById('s-people').textContent = DATA.summary.people_in_inventory;

if (DATA.insights.length > 0) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li class="flex items-start"><i class="zv-dot"></i><span>${i}</span></li>`).join('');
}

const gapColor = (gap, hc) => {
  if (!gap) return { bg: 'rgba(26,26,26,.05)', fg: 'rgba(26,26,26,.6)' };
  const r = hc ? Math.min(1, gap / hc) : 1;
  if (r >= 0.66) return { bg: '#FEE7EA', fg: '#B3172A' };
  if (r >= 0.34) return { bg: '#FFF2DA', fg: '#985704' };
  return { bg: '#DDF7EA', fg: '#0B7A43' };
};
document.getElementById('hm-tbody').innerHTML = DATA.heatmap.map(h => {
  let cells = '';
  for (let c = 1; c <= 5; c++) {
    if (c === h.criticality) {
      const bg = gapColor(h.gap, DATA.gaps.find(g => g.skill === h.skill)?.headcount_needed || 1);
      cells += `<td><div class="hm-cell" style="background:${bg.bg};color:${bg.fg}" title="gap ${h.gap}, cobertura ${h.coverage_pct}%">${h.gap}</div></td>`;
    } else {
      cells += `<td></td>`;
    }
  }
  return `<tr><td><strong>${esc(h.skill)}</strong></td>${cells}</tr>`;
}).join('');

document.getElementById('gap-tbody').innerHTML = DATA.gaps.map(g =>
  `<tr><td><strong>${esc(g.skill)}</strong></td><td>${g.required}</td><td>${g.criticality}</td><td>${g.headcount_needed}</td><td>${g.covered}</td><td class="${g.gap > 0 ? 'st-bad' : ''}">${g.gap}</td><td>${g.coverage_pct}%</td><td>${g.priority}</td><td><span class="pill rec-${g.recommendation}">${esc(g.recommendation)}</span></td><td class="text-zv-ink60 text-xs">${esc(g.rationale)}</td></tr>`).join('');

const bbbLabels = { BUILD: 'Build · treinar', BUY: 'Buy · contratar', BORROW: 'Borrow · contractor/parceiro' };
document.getElementById('bbb').innerHTML = ['BUILD','BUY','BORROW'].map(k => {
  const v = DATA.build_buy_borrow[k] || { count: 0, hc: 0 };
  return `<div class="bbb-tile"><div class="stat-label">${bbbLabels[k]}</div><div class="stat">${v.hc}</div><div class="text-sm text-zv-ink80 mt-2">${v.count} skill(s)</div></div>`;
}).join('');
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Análise de lacunas de capacidade (build/buy/borrow).")
    p.add_argument("--inventory", type=Path, required=True, help="CSV: person, skill, proficiency (1-5)")
    p.add_argument("--target", type=Path, required=True, help="CSV: skill, required_proficiency, criticality, headcount_needed")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    headers_i, inventory = load_csv(args.inventory)
    cols_inv = {k: auto_detect(headers_i, INV_ALIASES, k) for k in INV_ALIASES}
    if not cols_inv.get("skill") or not cols_inv.get("proficiency"):
        sys.exit("Inventory precisa de skill + proficiency. Verifique colunas.")

    headers_t, target = load_csv(args.target)
    cols_tgt = {k: auto_detect(headers_t, TARGET_ALIASES, k) for k in TARGET_ALIASES}
    if not cols_tgt.get("skill") or not cols_tgt.get("required_proficiency") or not cols_tgt.get("headcount_needed"):
        sys.exit("Target precisa de skill + required_proficiency + headcount_needed. Verifique colunas.")

    print(f"Inventory: {len(inventory)} linhas | Target: {len(target)} skills")
    data = analyze(inventory, target, cols_inv, cols_tgt)
    out = args.output or Path.cwd() / f"skills-gap-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    print(f"  {data['summary']['open_gaps']} gaps abertos | {data['summary']['total_gap_hc']} posições a fechar")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=skills-gap-analysis")
    return 0


if __name__ == "__main__":
    sys.exit(main())
