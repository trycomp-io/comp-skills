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
<meta charset="UTF-8"><title>Representation DEI Funnel — Comp</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  body{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b}
  .card{background:white;border-radius:12px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin-bottom:1.5rem}
  .stat{font-size:2.25rem;font-weight:800}
  .stat-label{font-size:.875rem;color:#64748b;text-transform:uppercase;font-weight:600}
  table{width:100%;border-collapse:collapse;font-size:.85rem}
  th{background:#1e293b;color:white;padding:.65rem;text-align:left;font-size:.75rem;text-transform:uppercase}
  td{padding:.65rem;border-bottom:1px solid #e2e8f0}
  .bar{display:flex;height:30px;border-radius:6px;overflow:hidden;font-size:.7rem;color:white;font-weight:600}
  .seg{display:flex;align-items:center;justify-content:center;min-width:24px}
  .leak{background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:.75rem 1rem;margin-bottom:.5rem}
  .legend{display:inline-flex;align-items:center;gap:.35rem;font-size:.75rem;margin-right:1rem}
  .swatch{width:12px;height:12px;border-radius:3px;display:inline-block}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-6xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Representation DEI Funnel</div>
<h1 class="text-3xl font-extrabold text-slate-900">Representatividade ao longo do ciclo</h1>
<p class="text-sm text-slate-500 mt-2" id="generated"></p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
<div class="card"><div class="stat-label">Recorte</div><div class="stat text-rose-600" id="s-dim"></div></div>
<div class="card"><div class="stat-label">Headcount</div><div class="stat" id="s-hc"></div></div>
<div class="card"><div class="stat-label">Liderança</div><div class="stat" id="s-lead"></div></div>
<div class="card"><div class="stat-label">Grupos</div><div class="stat" id="s-groups"></div></div>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-2">Mix por estágio</h2>
<div id="legend" class="mb-4"></div>
<div id="stages" class="space-y-4"></div>
<p class="text-xs text-slate-400 mt-4">Células com menos de 3 pessoas são omitidas por confidencialidade; percentuais são sobre o total visível de cada estágio.</p>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Insights</h2>
<ul class="space-y-2" id="insights-list"></ul>
</div>

<div class="card" id="leaks-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Pontos de vazamento</h2>
<div id="leaks"></div>
</div>

<div class="card" id="gap-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Gap de liderança vs geral</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Grupo</th><th>% Geral</th><th>% Liderança</th><th>Gap (p.p.)</th></tr></thead><tbody id="gap-tbody"></tbody></table></div>
</div>

<div class="card" id="rates-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Taxas por grupo</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Grupo</th><th>HC</th><th>Taxa de promoção</th><th>Taxa de saída</th></tr></thead><tbody id="rates-tbody"></tbody></table></div>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=representation-dei-funnel" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });
const PALETTE = ['#ff4456','#2563eb','#059669','#d97706','#7c3aed','#0891b2','#db2777','#65a30d','#475569','#ea580c'];
const colorFor = {};
DATA.summary.groups.forEach((g,i) => colorFor[g] = PALETTE[i % PALETTE.length]);

document.getElementById('s-dim').textContent = DATA.summary.dimension;
document.getElementById('s-hc').textContent = DATA.summary.roster_n;
document.getElementById('s-lead').textContent = DATA.summary.leaders_n;
document.getElementById('s-groups').textContent = DATA.summary.groups.length;

document.getElementById('legend').innerHTML = DATA.summary.groups.map(g =>
  `<span class="legend"><span class="swatch" style="background:${colorFor[g]}"></span>${esc(g)}</span>`).join('');

document.getElementById('stages').innerHTML = DATA.stages.map(s => {
  if (!s.available) return `<div><div class="text-sm font-semibold text-slate-700">${esc(s.stage)}</div><div class="text-xs text-slate-400">sem dados</div></div>`;
  const segs = DATA.summary.groups.filter(g => s.mix[g] !== undefined).map(g =>
    `<div class="seg" style="width:${s.mix[g]}%;background:${colorFor[g]}" title="${esc(g)}: ${s.mix[g]}%">${s.mix[g] >= 8 ? s.mix[g]+'%' : ''}</div>`).join('');
  const supp = s.suppressed > 0 ? ` <span class="text-xs text-slate-400">(+${s.suppressed} omitidos)</span>` : '';
  return `<div><div class="text-sm font-semibold text-slate-700 mb-1">${esc(s.stage)} <span class="text-slate-400 font-normal">— n=${s.n}</span>${supp}</div><div class="bar">${segs}</div></div>`;
}).join('');

if (DATA.insights.length > 0) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li class="flex items-start"><span class="text-rose-500 font-bold mr-2">●</span><span>${i}</span></li>`).join('');
}

if (DATA.leaks.length > 0) {
  document.getElementById('leaks-card').style.display = '';
  document.getElementById('leaks').innerHTML = DATA.leaks.map(l =>
    `<div class="leak"><strong>${esc(l.group)}</strong><ul class="list-disc ml-5 mt-1 text-sm text-slate-700">${l.notes.map(n => `<li>${esc(n)}</li>`).join('')}</ul></div>`).join('');
}

if (DATA.leadership_gap.length > 0) {
  document.getElementById('gap-card').style.display = '';
  document.getElementById('gap-tbody').innerHTML = DATA.leadership_gap.map(r =>
    `<tr><td><strong>${esc(r.group)}</strong></td><td>${r.overall_pct}%</td><td>${r.leadership_pct === null ? '—' : r.leadership_pct+'%'}</td><td class="${r.gap < 0 ? 'text-rose-600' : 'text-emerald-600'} font-semibold">${r.gap > 0 ? '+' : ''}${r.gap}</td></tr>`).join('');
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
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=representation-dei-funnel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
