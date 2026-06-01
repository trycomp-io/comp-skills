#!/usr/bin/env python3
"""
manager_scorecard.py — Diagnóstico de eficácia por gestor cruzando múltiplos
sinais (span, atrito do time, engajamento médio, taxa de promoção) num score
composto 0-100 com bandas e flags acionáveis.

Inputs:
  - Roster CSV: name, manager (mínimo). Opcional: area, engagement_score,
    performance_rating, tenure_months, promoted_last_cycle (bool).
  - Events CSV (opcional): manager, type (exit), regretted (bool).

Output: HTML executivo com ranking de gestores, scorecard por gestor,
distribuição de bandas e outliers.

Uso:
    python3 manager_scorecard.py --roster roster.csv
    python3 manager_scorecard.py --roster roster.csv --events exits.csv
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

SKILL_NAME = "manager-effectiveness-scorecard"
SKILL_VERSION = "1.0.0"

MIN_DIRECTS = 3  # confidencialidade: gestores com <3 directs viram "amostra pequena"

ROSTER_ALIASES = {
    "name":        ["name", "nome", "colaborador", "employee"],
    "manager":     ["manager", "gestor", "gerente", "lider", "líder", "reports_to", "manager_name"],
    "area":        ["area", "área", "departamento", "department", "time", "squad"],
    "engagement":  ["engagement_score", "engagement", "engajamento", "enps", "score_engajamento"],
    "performance": ["performance_rating", "performance", "desempenho", "rating", "nota"],
    "tenure":      ["tenure_months", "tenure", "tempo_casa", "meses_casa", "tempo_de_casa"],
    "promoted":    ["promoted_last_cycle", "promoted", "promovido", "promocao", "promoção"],
}
EVENT_ALIASES = {
    "manager":   ["manager", "gestor", "gerente", "lider", "líder", "reports_to"],
    "type":      ["type", "tipo", "event_type", "evento"],
    "regretted": ["regretted", "regret", "lamentavel", "lamentável", "regrettable"],
}


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
    s = str(v).strip().replace("%", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _bool(v):
    if v is None:
        return False
    return _norm(str(v)) in ("1", "true", "sim", "yes", "y", "s", "verdadeiro", "promovido")


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def band(score):
    if score is None:
        return "n/a"
    if score < 40:
        return "at-risk"
    if score < 60:
        return "developing"
    if score < 80:
        return "solid"
    return "exemplar"


def normalize_engagement(values):
    """Detecta escala (0-5, 0-10 ou 0-100) e retorna média em 0-100."""
    if not values:
        return None
    mx = max(values)
    if mx <= 5:
        scale = 5
    elif mx <= 10:
        scale = 10
    else:
        scale = 100
    return round(sum(values) / len(values) / scale * 100, 1)


def analyze(roster, cols_r, events, cols_e):
    # agrupa exits por gestor
    exits_by_mgr = defaultdict(lambda: {"total": 0, "regretted": 0})
    has_regretted = bool(cols_e.get("regretted")) if cols_e else False
    for e in (events or []):
        typ = _norm(e.get(cols_e.get("type") or "", "")) if cols_e.get("type") else "exit"
        if cols_e.get("type") and "exit" not in typ and "sai" not in typ and "deslig" not in typ:
            continue
        mgr = (e.get(cols_e.get("manager") or "") or "").strip()
        if not mgr:
            continue
        exits_by_mgr[mgr]["total"] += 1
        if has_regretted and _bool(e.get(cols_e["regretted"])):
            exits_by_mgr[mgr]["regretted"] += 1

    teams = defaultdict(list)
    for row in roster:
        mgr = (row.get(cols_r.get("manager") or "") or "").strip()
        if not mgr:
            continue
        teams[mgr].append(row)

    scorecards = []
    has_eng = bool(cols_r.get("engagement"))
    has_promo = bool(cols_r.get("promoted"))
    has_exits = bool(events)

    for mgr, directs in teams.items():
        span = len(directs)
        eng_vals = []
        if has_eng:
            for d in directs:
                v = _f(d.get(cols_r["engagement"]))
                if v is not None:
                    eng_vals.append(v)
        team_eng = normalize_engagement(eng_vals)  # 0-100 ou None

        promo_count = 0
        if has_promo:
            promo_count = sum(1 for d in directs if _bool(d.get(cols_r["promoted"])))
        promo_rate = round(promo_count / span * 100, 1) if (has_promo and span) else None

        ex = exits_by_mgr.get(mgr, {"total": 0, "regretted": 0})
        # atrito = saídas / (time atual + saídas) — denominador aproxima headcount do período
        denom = span + ex["total"]
        attrition = round(ex["total"] / denom * 100, 1) if (has_exits and denom) else None
        reg_attrition = round(ex["regretted"] / denom * 100, 1) if (has_exits and has_regretted and denom) else None
        # para score: usa regretted se disponível, senão total
        attrition_for_score = reg_attrition if reg_attrition is not None else attrition

        # ---- score composto 0-100 (blend transparente dos sinais disponíveis) ----
        comps = []  # (peso, valor 0-100)
        if team_eng is not None:
            comps.append((0.40, team_eng))
        if attrition_for_score is not None:
            # inverso: 0% atrito = 100; >=40% atrito = 0
            inv = max(0.0, min(100.0, 100 - attrition_for_score / 40 * 100))
            comps.append((0.30, round(inv, 1)))
        if promo_rate is not None:
            # 0% = 0; >=25% promo já é saudável = 100
            ps = max(0.0, min(100.0, promo_rate / 25 * 100))
            comps.append((0.15, round(ps, 1)))
        # span health: ideal 4-8; penaliza overloaded e underutilized
        if span >= 9:
            sh = max(0.0, 100 - (span - 8) * 8)
        elif span <= 3:
            sh = 50.0
        else:
            sh = 100.0
        comps.append((0.15, sh))

        wsum = sum(w for w, _ in comps)
        score = round(sum(w * v for w, v in comps) / wsum, 1) if wsum else None

        small_sample = span < MIN_DIRECTS

        flags = []
        if attrition_for_score is not None and attrition_for_score >= 20 and team_eng is not None and team_eng < 60:
            flags.append({"k": "at_risk", "label": "Gestor em risco — atrito alto + engajamento baixo"})
        if span > 12 and team_eng is not None and team_eng < 60:
            flags.append({"k": "overloaded", "label": "Sobrecarregado — span >12 com engajamento baixo"})
        elif span > 12:
            flags.append({"k": "overloaded", "label": "Span amplo (>12) — monitorar capacidade"})
        if 1 <= span <= 3:
            flags.append({"k": "underutilized", "label": "Subutilizado — span de 1 a 3 directs"})

        scorecards.append({
            "manager": mgr,
            "span": span,
            "team_engagement": team_eng,
            "attrition": attrition,
            "regretted_attrition": reg_attrition,
            "promo_rate": promo_rate,
            "promo_count": promo_count if has_promo else None,
            "score": score,
            "band": band(score) if not small_sample else "small",
            "small_sample": small_sample,
            "flags": flags,
            "components": [{"w": w, "v": v} for w, v in comps],
        })

    # rankings excluem amostra pequena
    ranked = sorted(
        [s for s in scorecards if not s["small_sample"] and s["score"] is not None],
        key=lambda s: -s["score"],
    )
    small = [s for s in scorecards if s["small_sample"]]

    distribution = defaultdict(int)
    for s in ranked:
        distribution[s["band"]] += 1

    scores_only = [s["score"] for s in ranked if s["score"] is not None]
    avg_score = round(sum(scores_only) / len(scores_only), 1) if scores_only else None

    at_risk = [s for s in ranked if s["band"] == "at-risk"]
    exemplar = [s for s in ranked if s["band"] == "exemplar"]

    insights = []
    if not ranked:
        insights.append("Nenhum gestor com 3+ directs pôde ser ranqueado — verifique a coluna de gestor no roster.")
    else:
        insights.append(f"<strong>{len(ranked)}</strong> gestores ranqueados (amostra ≥{MIN_DIRECTS} directs). Score médio: <strong>{avg_score}</strong>.")
        if exemplar:
            insights.append(f"<strong>{len(exemplar)}</strong> exemplar(es) — referências de práticas de gestão a escalar.")
        if at_risk:
            insights.append(f"<strong>{len(at_risk)}</strong> gestor(es) em risco (score <40) — priorizar conversa de desenvolvimento.")
        n_over = sum(1 for s in scorecards if any(f["k"] == "overloaded" for f in s["flags"]))
        n_under = sum(1 for s in scorecards if any(f["k"] == "underutilized" for f in s["flags"]))
        if n_over:
            insights.append(f"<strong>{n_over}</strong> gestor(es) sobrecarregado(s) (span amplo) — avaliar redistribuição de times.")
        if n_under:
            insights.append(f"<strong>{n_under}</strong> gestor(es) subutilizado(s) (1-3 directs) — oportunidade de consolidar camadas.")
        if small:
            insights.append(f"<strong>{len(small)}</strong> gestor(es) com amostra pequena (&lt;{MIN_DIRECTS} directs) exibidos sem ranking, por confidencialidade.")

    return {
        "summary": {
            "managers_ranked": len(ranked),
            "managers_total": len(scorecards),
            "small_sample": len(small),
            "avg_score": avg_score,
            "has_engagement": has_eng,
            "has_exits": has_exits,
            "has_promo": has_promo,
        },
        "distribution": {k: distribution[k] for k in ("at-risk", "developing", "solid", "exemplar")},
        "ranked": ranked,
        "small": small,
        "insights": insights,
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>Manager Effectiveness Scorecard — Comp</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  body{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b}
  .card{background:white;border-radius:12px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin-bottom:1.5rem}
  .stat{font-size:2.25rem;font-weight:800}
  .stat-label{font-size:.875rem;color:#64748b;text-transform:uppercase;font-weight:600}
  table{width:100%;border-collapse:collapse;font-size:.85rem}
  th{background:#1e293b;color:white;padding:.65rem;text-align:left;font-size:.75rem;text-transform:uppercase}
  td{padding:.65rem;border-bottom:1px solid #e2e8f0;vertical-align:top}
  .b-atrisk{background:#fee2e2;color:#991b1b}
  .b-developing{background:#fef3c7;color:#92400e}
  .b-solid{background:#dbeafe;color:#1e40af}
  .b-exemplar{background:#d1fae5;color:#065f46}
  .b-small{background:#f1f5f9;color:#475569}
  .pill{display:inline-block;padding:.2rem .55rem;border-radius:999px;font-size:.7rem;font-weight:600}
  .flag{display:inline-block;padding:.15rem .5rem;border-radius:6px;font-size:.7rem;font-weight:600;margin:.1rem;background:#fff7ed;color:#9a3412;border:1px solid #fed7aa}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-6xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Manager Effectiveness Scorecard</div>
<h1 class="text-3xl font-extrabold text-slate-900">Eficácia por gestor</h1>
<p class="text-sm text-slate-500 mt-2" id="generated"></p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
<div class="card"><div class="stat-label">Gestores ranqueados</div><div class="stat" id="s-ranked"></div></div>
<div class="card"><div class="stat-label">Total de gestores</div><div class="stat" id="s-total"></div></div>
<div class="card"><div class="stat-label">Score médio</div><div class="stat text-rose-600" id="s-avg"></div></div>
<div class="card"><div class="stat-label">Amostra pequena</div><div class="stat" id="s-small"></div></div>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Distribuição por banda</h2>
<div class="grid sm:grid-cols-4 gap-3" id="dist"></div>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Insights</h2>
<ul class="space-y-2" id="insights-list"></ul>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Ranking de gestores</h2>
<div class="overflow-x-auto"><table><thead><tr><th>#</th><th>Gestor</th><th>Banda</th><th>Score</th><th>Span</th><th>Engaj.</th><th>Atrito</th><th>Promo</th><th>Flags</th></tr></thead><tbody id="rank-tbody"></tbody></table></div>
</div>

<div class="card" id="small-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Amostra pequena (sem ranking)</h2>
<p class="text-sm text-slate-500 mb-3">Gestores com menos de 3 directs. Exibidos por contexto, fora de rankings e médias, por confidencialidade.</p>
<div class="overflow-x-auto"><table><thead><tr><th>Gestor</th><th>Span</th><th>Engaj.</th><th>Atrito</th><th>Promo</th><th>Flags</th></tr></thead><tbody id="small-tbody"></tbody></table></div>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=manager-effectiveness-scorecard" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });
const pct = v => (v === null || v === undefined) ? '—' : v + '%';
const num = v => (v === null || v === undefined) ? '—' : v;

document.getElementById('s-ranked').textContent = DATA.summary.managers_ranked;
document.getElementById('s-total').textContent = DATA.summary.managers_total;
document.getElementById('s-avg').textContent = num(DATA.summary.avg_score);
document.getElementById('s-small').textContent = DATA.summary.small_sample;

const bandLabels = { 'at-risk':'At-risk (<40)', developing:'Developing (40-59)', solid:'Solid (60-79)', exemplar:'Exemplar (80+)' };
const bandClass = { 'at-risk':'b-atrisk', developing:'b-developing', solid:'b-solid', exemplar:'b-exemplar', small:'b-small' };
document.getElementById('dist').innerHTML = ['at-risk','developing','solid','exemplar'].map(k =>
  `<div class="${bandClass[k]} rounded-lg p-4 text-center">
    <div class="text-3xl font-bold">${DATA.distribution[k] || 0}</div>
    <div class="text-xs font-semibold mt-1">${bandLabels[k]}</div>
  </div>`).join('');

if (DATA.insights.length > 0) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li class="flex items-start"><span class="text-rose-500 font-bold mr-2">●</span><span>${i}</span></li>`).join('');
}

const flagsHtml = fl => fl.length ? fl.map(f => `<span class="flag">${f.label}</span>`).join('') : '<span class="text-slate-400">—</span>';
const bandPill = b => `<span class="pill ${bandClass[b]}">${b === 'small' ? 'amostra pequena' : b}</span>`;

document.getElementById('rank-tbody').innerHTML = DATA.ranked.map((s, i) =>
  `<tr><td><strong>${i+1}</strong></td><td><strong>${esc(s.manager)}</strong></td><td>${bandPill(s.band)}</td><td><strong>${num(s.score)}</strong></td><td>${s.span}</td><td>${pct(s.team_engagement)}</td><td>${pct(s.regretted_attrition !== null ? s.regretted_attrition : s.attrition)}</td><td>${pct(s.promo_rate)}</td><td>${flagsHtml(s.flags)}</td></tr>`).join('');

if (DATA.small.length > 0) {
  document.getElementById('small-card').style.display = '';
  document.getElementById('small-tbody').innerHTML = DATA.small.map(s =>
    `<tr><td><strong>${esc(s.manager)}</strong></td><td>${s.span}</td><td>${pct(s.team_engagement)}</td><td>${pct(s.regretted_attrition !== null ? s.regretted_attrition : s.attrition)}</td><td>${pct(s.promo_rate)}</td><td>${flagsHtml(s.flags)}</td></tr>`).join('');
}
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Scorecard de eficácia de gestores.")
    p.add_argument("--roster", type=Path, required=True)
    p.add_argument("--events", type=Path, help="CSV opcional de saídas (manager, type, regretted)")
    p.add_argument("--output", type=Path)
    p.add_argument("--manager-col"); p.add_argument("--engagement-col")
    p.add_argument("--promoted-col")
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    headers_r, roster = load_csv(args.roster)
    cols_r = {k: auto_detect(headers_r, ROSTER_ALIASES, k) for k in ROSTER_ALIASES}
    if args.manager_col: cols_r["manager"] = args.manager_col
    if args.engagement_col: cols_r["engagement"] = args.engagement_col
    if args.promoted_col: cols_r["promoted"] = args.promoted_col
    if not cols_r.get("manager"):
        sys.exit("Roster precisa de uma coluna de gestor (manager). Verifique colunas.")

    events, cols_e = [], {}
    if args.events:
        headers_e, events = load_csv(args.events)
        cols_e = {k: auto_detect(headers_e, EVENT_ALIASES, k) for k in EVENT_ALIASES}
        if not cols_e.get("manager"):
            sys.exit("Events CSV precisa de coluna de gestor (manager).")

    print(f"Roster: {len(roster)} linhas | Events: {len(events)} | gestor='{cols_r.get('manager')}'")
    data = analyze(roster, cols_r, events, cols_e)
    out = args.output or Path.cwd() / f"manager-scorecard-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    print(f"  {data['summary']['managers_ranked']} gestores ranqueados | score médio: {data['summary']['avg_score']}")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=manager-effectiveness-scorecard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
