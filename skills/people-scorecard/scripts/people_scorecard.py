#!/usr/bin/env python3
"""
people_scorecard.py — Pacote canônico de People analytics a partir de um
roster CSV (+ opcional CSV de eventos). Gera um scorecard executivo de uma
página: headcount, attrition, tenure, span of control, mobilidade interna,
representatividade (com regra de confidencialidade) e crescimento.

Inputs:
  - Roster CSV (atual): name, area, level, manager (opc), gender (opc),
    tenure_months OU hire_date, salary (opc).
  - Events CSV (opc): type (hire/exit/promotion), date, regretted (opc).

Output: HTML dashboard executivo (tiles + tabelas + tendência se houver datas).

Uso:
    python3 people_scorecard.py --roster roster.csv [--events events.csv]
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
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

SKILL_NAME = "people-scorecard"
SKILL_VERSION = "1.0.0"

MIN_GROUP = 3  # regra de confidencialidade: grupos < 3 são suprimidos


ROSTER_ALIASES = {
    "name":     ["name", "nome", "colaborador", "employee", "funcionario"],
    "area":     ["area", "área", "departamento", "department", "time", "squad"],
    "level":    ["level", "nivel", "nível", "senioridade", "grade", "cargo_nivel"],
    "manager":  ["manager", "gestor", "gerente", "lider", "líder", "reports_to"],
    "gender":   ["gender", "genero", "gênero", "sexo", "sex"],
    "tenure":   ["tenure_months", "tenure", "tempo_de_casa", "meses_de_casa", "meses_casa"],
    "hire_date":["hire_date", "data_admissao", "data_de_admissao", "admissao", "start_date", "data_contratacao"],
    "salary":   ["salary", "salario", "salário", "salario_base"],
}
EVENT_ALIASES = {
    "type":     ["type", "tipo", "event", "evento", "movimento"],
    "date":     ["date", "data", "event_date", "data_evento"],
    "regretted":["regretted", "lamentavel", "lamentável", "regretted_exit", "voluntario_lamentavel"],
    "area":     ["area", "área", "departamento", "department"],
}

# níveis considerados liderança (heurística por substring, ajustável)
LEADER_HINTS = ["lead", "líder", "lider", "head", "manager", "gestor", "gerente",
                "director", "diretor", "vp", "chief", "c-level", "principal", "staff",
                "l5", "l6", "l7", "l8", "senior_manager"]


def _norm(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii").strip().lower().replace(" ", "_")


def auto_detect(headers, aliases, key):
    h = {_norm(x): x for x in headers}
    for cand in aliases[key]:
        if _norm(cand) in h:
            return h[_norm(cand)]
    return None


def _f(v):
    if v is None or v == "":
        return None
    s = str(v).strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def _truthy(v):
    return _norm(v) in ("1", "true", "sim", "yes", "y", "s", "x")


def parse_date(v):
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y", "%Y-%m"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def norm_gender(v):
    n = _norm(v)
    if n in ("f", "female", "feminino", "fem", "mulher", "w"):
        return "F"
    if n in ("m", "male", "masculino", "masc", "homem"):
        return "M"
    return None


def is_leader(level):
    nl = _norm(level)
    return any(h in nl for h in LEADER_HINTS)


def months_between(d1, d2):
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def analyze(roster, cols_r, events, cols_e):
    now = datetime.now()
    total = len(roster)

    by_area = defaultdict(int)
    by_level = defaultdict(int)
    tenures = []
    by_gender = defaultdict(int)
    leader_gender = defaultdict(int)
    leader_total = 0
    reports_per_mgr = defaultdict(int)
    has_manager_col = bool(cols_r.get("manager"))

    for row in roster:
        area = (row.get(cols_r.get("area") or "") or "—").strip() or "—"
        level = (row.get(cols_r.get("level") or "") or "—").strip() or "—"
        by_area[area] += 1
        by_level[level] += 1

        # tenure
        ten = _f(row.get(cols_r["tenure"])) if cols_r.get("tenure") else None
        if ten is None and cols_r.get("hire_date"):
            d = parse_date(row.get(cols_r["hire_date"]))
            if d:
                ten = months_between(d, now)
        if ten is not None and ten >= 0:
            tenures.append(ten)

        # gender + leadership representation
        if cols_r.get("gender"):
            g = norm_gender(row.get(cols_r["gender"]))
            if g:
                by_gender[g] += 1
                if is_leader(level):
                    leader_total += 1
                    leader_gender[g] += 1

        # span of control
        if has_manager_col:
            mgr = (row.get(cols_r["manager"]) or "").strip()
            if mgr:
                reports_per_mgr[mgr] += 1

    # ---- Headcount ----
    headcount = {
        "total": total,
        "by_area": sorted([{"name": k, "hc": v} for k, v in by_area.items()], key=lambda x: -x["hc"]),
        "by_level": sorted([{"name": k, "hc": v} for k, v in by_level.items()], key=lambda x: -x["hc"]),
    }

    # ---- Tenure ----
    tenure_stats = None
    if tenures:
        buckets = {"0-12m": 0, "12-24m": 0, "24-48m": 0, "48m+": 0}
        for t in tenures:
            if t < 12: buckets["0-12m"] += 1
            elif t < 24: buckets["12-24m"] += 1
            elif t < 48: buckets["24-48m"] += 1
            else: buckets["48m+"] += 1
        tenure_stats = {
            "avg_months": round(statistics.mean(tenures), 1),
            "median_months": round(statistics.median(tenures), 1),
            "distribution": buckets,
        }

    # ---- Span of control ----
    span_stats = None
    if has_manager_col and reports_per_mgr:
        spans = list(reports_per_mgr.values())
        sbuckets = {"1-3": 0, "4-7": 0, "8-12": 0, "13+": 0}
        for s in spans:
            if s <= 3: sbuckets["1-3"] += 1
            elif s <= 7: sbuckets["4-7"] += 1
            elif s <= 12: sbuckets["8-12"] += 1
            else: sbuckets["13+"] += 1
        span_stats = {
            "managers": len(spans),
            "avg_span": round(statistics.mean(spans), 1),
            "max_span": max(spans),
            "distribution": sbuckets,
        }

    # ---- Representatividade (confidencialidade < 3 suprimida) ----
    representation = None
    if by_gender:
        total_gendered = sum(by_gender.values())
        overall = {}
        for g in ("F", "M"):
            c = by_gender.get(g, 0)
            overall[g] = {"count": c if c >= MIN_GROUP else None,
                          "pct": round(c / total_gendered * 100, 1) if (c >= MIN_GROUP and total_gendered) else None}
        leadership = None
        if leader_total >= MIN_GROUP:
            leadership = {}
            for g in ("F", "M"):
                c = leader_gender.get(g, 0)
                leadership[g] = {"count": c if c >= MIN_GROUP else None,
                                 "pct": round(c / leader_total * 100, 1) if (c >= MIN_GROUP and leader_total) else None}
        representation = {
            "overall": overall, "total_gendered": total_gendered,
            "leadership": leadership, "leader_total": leader_total if leader_total >= MIN_GROUP else None,
            "suppressed": any(by_gender.get(g, 0) < MIN_GROUP and by_gender.get(g, 0) > 0 for g in ("F", "M")),
        }

    # ---- Eventos: attrition, mobilidade, crescimento, tendência ----
    flows = None
    trend = None
    if events is not None and cols_e.get("type"):
        hires = exits = promos = regretted_exits = 0
        dated_exits = []
        monthly = defaultdict(lambda: {"hire": 0, "exit": 0, "promotion": 0})
        for ev in events:
            t = _norm(ev.get(cols_e["type"]))
            d = parse_date(ev.get(cols_e["date"])) if cols_e.get("date") else None
            key = d.strftime("%Y-%m") if d else None
            if t in ("hire", "contratacao", "admissao", "admission"):
                hires += 1
                if key: monthly[key]["hire"] += 1
            elif t in ("exit", "desligamento", "saida", "termination", "exit_voluntario"):
                exits += 1
                if key:
                    monthly[key]["exit"] += 1
                    dated_exits.append(d)
                if cols_e.get("regretted") and _truthy(ev.get(cols_e["regretted"])):
                    regretted_exits += 1
            elif t in ("promotion", "promocao", "promoção", "promo"):
                promos += 1
                if key: monthly[key]["promotion"] += 1

        # avg headcount: aproxima por headcount atual + metade do fluxo líquido
        avg_hc = total + (exits - hires) / 2 if total else total
        avg_hc = max(avg_hc, 1)
        # janela do período pelos eventos datados (default 12m)
        period_months = 12
        all_dates = [parse_date(ev.get(cols_e["date"])) for ev in events if cols_e.get("date")]
        all_dates = [d for d in all_dates if d]
        if len(all_dates) >= 2:
            span_m = months_between(min(all_dates), max(all_dates)) + 1
            period_months = max(1, span_m)
        annualize = 12 / period_months
        flows = {
            "hires": hires, "exits": exits, "promotions": promos,
            "regretted_exits": regretted_exits,
            "period_months": period_months,
            "attrition_rate": round(exits / avg_hc * annualize * 100, 1),
            "regretted_rate": round(regretted_exits / avg_hc * annualize * 100, 1) if cols_e.get("regretted") else None,
            "internal_mobility_rate": round(promos / total * 100, 1) if total else 0,
            "growth_rate": round((hires - exits) / total * 100, 1) if total else 0,
            "new_hire_rate": round(hires / total * 100, 1) if total else 0,
        }
        if monthly:
            trend = [{"month": k, **monthly[k]} for k in sorted(monthly)]

    # ---- Insights ----
    insights = []
    insights.append(f"Headcount atual: <strong>{total}</strong> em {len(by_area)} área(s) e {len(by_level)} nível(is).")
    if tenure_stats:
        insights.append(f"Tenure médio: <strong>{tenure_stats['avg_months']} meses</strong> (mediana {tenure_stats['median_months']}).")
    if span_stats:
        insights.append(f"Span of control médio: <strong>{span_stats['avg_span']}</strong> reportes por gestor (máx {span_stats['max_span']}).")
    if flows:
        insights.append(f"Attrition anualizada: <strong>{flows['attrition_rate']}%</strong>"
                        + (f" (lamentável {flows['regretted_rate']}%)" if flows['regretted_rate'] is not None else "")
                        + f" · mobilidade interna {flows['internal_mobility_rate']}% · crescimento {flows['growth_rate']}%.")
    if representation and representation["overall"].get("F", {}).get("pct") is not None:
        msg = f"Representatividade feminina geral: <strong>{representation['overall']['F']['pct']}%</strong>"
        if representation.get("leadership") and representation["leadership"].get("F", {}).get("pct") is not None:
            msg += f" · em liderança: <strong>{representation['leadership']['F']['pct']}%</strong>"
        insights.append(msg + ".")
    if representation and representation.get("suppressed"):
        insights.append("Alguns grupos de gênero foram suprimidos por terem menos de 3 pessoas (regra de confidencialidade).")

    return {
        "summary": {
            "headcount": total,
            "areas": len(by_area),
            "levels": len(by_level),
            "attrition_rate": flows["attrition_rate"] if flows else None,
            "internal_mobility_rate": flows["internal_mobility_rate"] if flows else None,
            "avg_tenure": tenure_stats["avg_months"] if tenure_stats else None,
            "avg_span": span_stats["avg_span"] if span_stats else None,
        },
        "headcount": headcount,
        "tenure": tenure_stats,
        "span": span_stats,
        "representation": representation,
        "flows": flows,
        "trend": trend,
        "insights": insights,
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>People Scorecard — Comp</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  body{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b}
  .card{background:white;border-radius:12px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin-bottom:1.5rem}
  .stat{font-size:2.25rem;font-weight:800}
  .stat-label{font-size:.8rem;color:#64748b;text-transform:uppercase;font-weight:600}
  table{width:100%;border-collapse:collapse;font-size:.85rem}
  th{background:#1e293b;color:white;padding:.6rem;text-align:left;font-size:.72rem;text-transform:uppercase}
  td{padding:.6rem;border-bottom:1px solid #e2e8f0}
  .bar{height:8px;border-radius:4px;background:#ff4456}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-6xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">People Scorecard</div>
<h1 class="text-3xl font-extrabold text-slate-900">Pacote mensal de People analytics</h1>
<p class="text-sm text-slate-500 mt-2" id="generated"></p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-6" id="tiles"></div>

<div class="card" id="insights-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Resumo</h2>
<ul class="space-y-2" id="insights-list"></ul>
</div>

<div class="grid sm:grid-cols-2 gap-6">
<div class="card"><h2 class="text-xl font-bold mb-4">Headcount por área</h2><div class="overflow-x-auto"><table><thead><tr><th>Área</th><th>HC</th><th>%</th></tr></thead><tbody id="area-tbody"></tbody></table></div></div>
<div class="card"><h2 class="text-xl font-bold mb-4">Headcount por nível</h2><div class="overflow-x-auto"><table><thead><tr><th>Nível</th><th>HC</th><th>%</th></tr></thead><tbody id="level-tbody"></tbody></table></div></div>
</div>

<div class="grid sm:grid-cols-2 gap-6">
<div class="card" id="tenure-card"><h2 class="text-xl font-bold mb-4">Distribuição de tenure</h2><div class="overflow-x-auto"><table><thead><tr><th>Faixa</th><th>HC</th></tr></thead><tbody id="tenure-tbody"></tbody></table></div></div>
<div class="card" id="span-card"><h2 class="text-xl font-bold mb-4">Span of control</h2><div class="overflow-x-auto"><table><thead><tr><th>Reportes</th><th>Gestores</th></tr></thead><tbody id="span-tbody"></tbody></table></div></div>
</div>

<div class="card" id="rep-card" style="display:none;">
<h2 class="text-xl font-bold mb-1">Representatividade de gênero</h2>
<p class="text-xs text-slate-500 mb-4">Grupos com menos de 3 pessoas são suprimidos (—) por confidencialidade.</p>
<div class="grid sm:grid-cols-2 gap-6" id="rep-body"></div>
</div>

<div class="card" id="trend-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Tendência do período</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Mês</th><th>Contratações</th><th>Saídas</th><th>Promoções</th></tr></thead><tbody id="trend-tbody"></tbody></table></div>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=people-scorecard" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });
const pct = (n, d) => d ? (n / d * 100).toFixed(1) + '%' : '—';

const s = DATA.summary;
const tiles = [
  { label: 'Headcount', value: s.headcount },
  { label: 'Áreas', value: s.areas },
  { label: 'Attrition anual.', value: s.attrition_rate != null ? s.attrition_rate + '%' : '—', color: 'text-rose-600' },
  { label: 'Mobilidade interna', value: s.internal_mobility_rate != null ? s.internal_mobility_rate + '%' : '—' },
  { label: 'Tenure médio (m)', value: s.avg_tenure != null ? s.avg_tenure : '—' },
  { label: 'Span médio', value: s.avg_span != null ? s.avg_span : '—' },
];
document.getElementById('tiles').innerHTML = tiles.map(t =>
  `<div class="card"><div class="stat-label">${t.label}</div><div class="stat ${t.color||''}">${t.value}</div></div>`).join('');

if (DATA.insights.length) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li class="flex items-start"><span class="text-rose-500 font-bold mr-2">●</span><span>${i}</span></li>`).join('');
}

document.getElementById('area-tbody').innerHTML = DATA.headcount.by_area.map(a =>
  `<tr><td><strong>${esc(a.name)}</strong></td><td>${a.hc}</td><td>${pct(a.hc, s.headcount)}</td></tr>`).join('');
document.getElementById('level-tbody').innerHTML = DATA.headcount.by_level.map(l =>
  `<tr><td><strong>${esc(l.name)}</strong></td><td>${l.hc}</td><td>${pct(l.hc, s.headcount)}</td></tr>`).join('');

if (DATA.tenure) {
  document.getElementById('tenure-tbody').innerHTML = Object.entries(DATA.tenure.distribution).map(([k, v]) =>
    `<tr><td>${esc(k)}</td><td>${v}</td></tr>`).join('');
} else { document.getElementById('tenure-card').style.display = 'none'; }

if (DATA.span) {
  document.getElementById('span-tbody').innerHTML = Object.entries(DATA.span.distribution).map(([k, v]) =>
    `<tr><td>${esc(k)} reportes</td><td>${v}</td></tr>`).join('');
} else { document.getElementById('span-card').style.display = 'none'; }

if (DATA.representation) {
  const r = DATA.representation;
  const blk = (title, obj, tot) => {
    if (!obj) return `<div><h3 class="font-semibold mb-2">${title}</h3><p class="text-sm text-slate-400">Grupo total &lt; 3 — suprimido por confidencialidade.</p></div>`;
    const rows = ['F','M'].map(g => {
      const c = obj[g] && obj[g].count != null ? obj[g].count : '—';
      const p = obj[g] && obj[g].pct != null ? obj[g].pct + '%' : '—';
      return `<tr><td>${g === 'F' ? 'Feminino' : 'Masculino'}</td><td>${c}</td><td>${p}</td></tr>`;
    }).join('');
    return `<div><h3 class="font-semibold mb-2">${title}${tot ? ' (n=' + tot + ')' : ''}</h3><table><thead><tr><th>Gênero</th><th>HC</th><th>%</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  };
  document.getElementById('rep-card').style.display = '';
  document.getElementById('rep-body').innerHTML =
    blk('Geral', r.overall, r.total_gendered) + blk('Liderança', r.leadership, r.leader_total);
}

if (DATA.trend && DATA.trend.length) {
  document.getElementById('trend-card').style.display = '';
  document.getElementById('trend-tbody').innerHTML = DATA.trend.map(m =>
    `<tr><td><strong>${esc(m.month)}</strong></td><td>${m.hire}</td><td class="text-rose-600">${m.exit}</td><td class="text-emerald-600">${m.promotion}</td></tr>`).join('');
}
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="People scorecard executivo a partir de um roster CSV (+ eventos opcional).")
    p.add_argument("--roster", type=Path, required=True)
    p.add_argument("--events", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    headers_r, roster = load_csv(args.roster)
    cols_r = {k: auto_detect(headers_r, ROSTER_ALIASES, k) for k in ROSTER_ALIASES}
    if not roster:
        sys.exit("Roster vazio.")

    events, cols_e = None, {}
    if args.events:
        headers_e, events = load_csv(args.events)
        cols_e = {k: auto_detect(headers_e, EVENT_ALIASES, k) for k in EVENT_ALIASES}
        if not cols_e.get("type"):
            print("Aviso: events CSV sem coluna 'type' reconhecida — taxas e tendência serão omitidas.")
            events = None

    print(f"Roster: {len(roster)} | colunas: " + ", ".join(f"{k}={v}" for k, v in cols_r.items() if v))
    if events is not None:
        print(f"Eventos: {len(events)}")
    data = analyze(roster, cols_r, events, cols_e)
    out = args.output or Path.cwd() / f"people-scorecard-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    line = f"  HC {data['summary']['headcount']}"
    if data['summary']['attrition_rate'] is not None:
        line += f" | attrition {data['summary']['attrition_rate']}%"
    if data['summary']['avg_tenure'] is not None:
        line += f" | tenure médio {data['summary']['avg_tenure']}m"
    print(line)

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=people-scorecard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
