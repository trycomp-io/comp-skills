#!/usr/bin/env python3
"""
flight_risk.py — Scoring EXPLICÁVEL de risco de saída (flight risk) por
colaborador, a partir de um roster CSV. Não é caixa-preta: cada ponto de
risco é atribuído a um fator transparente e documentado.

Input roster CSV (auto-detect, aliases PT/EN):
  name, area, manager (opc), tenure_months, comp_ratio (ou salary + band_mid),
  months_since_last_promo (opc), engagement_score (eNPS -100..100 OU 1-5),
  performance_rating (opc, 1-5 ou labels), level (opc).

Output: HTML executivo com lista priorizada de risco, breakdown por fator,
distribuição por banda, áreas/gestores mais quentes, alavancas sugeridas.

Uso:
    python3 flight_risk.py --roster roster.csv
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

SKILL_NAME = "flight-risk-forecast"
SKILL_VERSION = "1.0.0"


ROSTER_ALIASES = {
    "name":      ["name", "nome", "colaborador", "employee", "funcionario"],
    "area":      ["area", "área", "departamento", "department", "time", "squad"],
    "manager":   ["manager", "gestor", "gerente", "lider", "líder", "reports_to"],
    "tenure":    ["tenure_months", "tenure", "tempo_de_casa", "tempo_casa", "meses_de_casa", "meses_casa"],
    "comp_ratio":["comp_ratio", "compa_ratio", "compratio", "compa"],
    "salary":    ["salary", "salario", "salário", "salario_base"],
    "band_mid":  ["band_mid", "mid", "mediana", "median", "p50", "midpoint"],
    "promo":     ["months_since_last_promo", "meses_desde_ultima_promocao", "meses_ultima_promocao", "tempo_sem_promocao", "months_since_promo"],
    "engagement":["engagement_score", "engagement", "engajamento", "enps", "e_nps", "score_engajamento"],
    "performance":["performance_rating", "performance", "desempenho", "nota_desempenho", "rating", "avaliacao"],
    "level":     ["level", "nivel", "nível", "senioridade", "grade"],
    "exited":    ["exited", "exit", "desligado", "saiu", "left"],
}

# Pesos máximos por fator (documentados — soma teórica = 100)
W_COMP = 25        # comp_ratio abaixo da mediana
W_PROMO = 20       # tempo sem promoção
W_ENGAGEMENT = 35  # engajamento (maior driver isolado)
W_TENURE = 12      # janela de churn (12-24 meses)
W_MANAGER = 8      # gestor com attrition alta (só se houver exit info)


def _esc(v):
    import html
    return html.escape(str(v), quote=True) if v is not None else ""


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
    s = str(v).strip().replace("%", "")
    # formato BR: 1.234,56 -> 1234.56 ; mas "0.90" deve virar 0.90
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
    return _norm(v) in ("1", "true", "sim", "yes", "y", "s", "x", "desligado", "saiu", "left", "exit", "exited")


def normalize_engagement(raw):
    """Retorna engajamento normalizado em 0..1 (1 = ótimo) + a escala detectada.
    eNPS -100..100 -> (x+100)/200 ; escala 1-5 -> (x-1)/4."""
    if raw is None:
        return None, None
    if raw < -1 or raw > 5:  # claramente eNPS
        return max(0.0, min(1.0, (raw + 100) / 200)), "enps"
    if raw <= 5:  # escala 1-5
        return max(0.0, min(1.0, (raw - 1) / 4)), "1-5"
    return max(0.0, min(1.0, (raw + 100) / 200)), "enps"


def normalize_performance(raw):
    """Retorna rating 1-5 (float) ou None. Aceita labels comuns."""
    if raw is None or str(raw).strip() == "":
        return None
    n = _f(raw)
    if n is not None and 1 <= n <= 5:
        return n
    label = _norm(raw)
    labels = {
        "low": 1, "baixo": 1, "abaixo": 2, "below": 2,
        "meets": 3, "atende": 3, "medio": 3, "médio": 3, "ok": 3,
        "exceeds": 4, "acima": 4, "supera": 4, "alto": 4,
        "outstanding": 5, "excepcional": 5, "top": 5, "excelente": 5,
    }
    return labels.get(label)


def band(score):
    if score <= 25: return "low"
    if score <= 50: return "medium"
    if score <= 75: return "high"
    return "critical"


def score_employee(emp, mgr_attrition):
    """Retorna (score, factors[]) — cada factor é explicável."""
    factors = []
    score = 0.0

    cr = emp.get("comp_ratio")
    if cr is not None and cr < 0.90:
        # quanto mais abaixo de 1.0, mais pontos; piso em 0.70
        deficit = min(1.0, (0.90 - max(0.70, cr)) / 0.20)
        pts = round(W_COMP * deficit, 1)
        if pts > 0:
            score += pts
            factors.append({"factor": "Comp abaixo do mercado", "points": pts,
                            "detail": f"Compa-ratio {cr:.2f} (abaixo de 0,90)"})

    promo = emp.get("promo")
    if promo is not None and promo > 24:
        frac = min(1.0, (promo - 24) / 24)  # satura em 48 meses
        pts = round(W_PROMO * frac, 1)
        if pts > 0:
            score += pts
            factors.append({"factor": "Estagnação de carreira", "points": pts,
                            "detail": f"{int(promo)} meses sem promoção"})

    eng = emp.get("engagement_norm")
    if eng is not None and eng < 0.5:
        frac = (0.5 - eng) / 0.5  # 0 em 0.5, 1 em 0
        pts = round(W_ENGAGEMENT * frac, 1)
        if pts > 0:
            score += pts
            factors.append({"factor": "Baixo engajamento", "points": pts,
                            "detail": "Engajamento abaixo do ponto neutro"})

    ten = emp.get("tenure")
    if ten is not None and 12 <= ten <= 24:
        # pico de risco no meio da janela
        prox = 1 - abs(ten - 18) / 6  # 1 em 18m, ~0 nas bordas
        pts = round(W_TENURE * max(0.4, prox), 1)
        score += pts
        factors.append({"factor": "Janela de churn", "points": pts,
                        "detail": f"{int(ten)} meses de casa (faixa 12-24m)"})

    mgr = emp.get("manager")
    if mgr and mgr_attrition.get(mgr, 0) > 0:
        rate = mgr_attrition[mgr]
        pts = round(W_MANAGER * min(1.0, rate / 0.30), 1)  # satura em 30% attrition
        if pts > 0:
            score += pts
            factors.append({"factor": "Gestor com saídas altas", "points": pts,
                            "detail": f"Attrition do time de {mgr}: {rate*100:.0f}%"})

    score = round(min(100.0, score), 1)
    factors.sort(key=lambda x: -x["points"])
    return score, factors


LEVERS = {
    "Comp abaixo do mercado": "Revisão salarial / ajuste pra mediana da banda",
    "Estagnação de carreira": "Plano de carreira + conversa sobre próximo passo / promoção",
    "Baixo engajamento": "Conversa 1:1 estruturada, entender driver, plano de ação do gestor",
    "Janela de churn": "Check-in de retenção proativo, reforçar pertencimento e propósito",
    "Gestor com saídas altas": "Apoio/coaching ao gestor + diagnóstico de clima do time",
}


def analyze(roster, cols):
    # Pré-processa colaboradores
    emps = []
    for row in roster:
        name = (row.get(cols.get("name") or "") or "").strip()
        if not name:
            continue
        area = (row.get(cols.get("area") or "") or "—").strip() or "—"
        manager = (row.get(cols.get("manager") or "") or "").strip()
        level = (row.get(cols.get("level") or "") or "").strip()

        cr = _f(row.get(cols["comp_ratio"])) if cols.get("comp_ratio") else None
        if cr is None and cols.get("salary") and cols.get("band_mid"):
            sal = _f(row.get(cols["salary"]))
            mid = _f(row.get(cols["band_mid"]))
            if sal and mid and mid > 0:
                cr = round(sal / mid, 3)

        eng_raw = _f(row.get(cols["engagement"])) if cols.get("engagement") else None
        eng_norm, eng_scale = normalize_engagement(eng_raw)
        perf = normalize_performance(row.get(cols["performance"])) if cols.get("performance") else None

        emps.append({
            "name": name, "area": area, "manager": manager, "level": level,
            "comp_ratio": cr,
            "tenure": _f(row.get(cols["tenure"])) if cols.get("tenure") else None,
            "promo": _f(row.get(cols["promo"])) if cols.get("promo") else None,
            "engagement_norm": eng_norm, "engagement_scale": eng_scale,
            "performance": perf,
            "exited": _truthy(row.get(cols["exited"])) if cols.get("exited") else False,
        })

    # Attrition por gestor (só se houver coluna exit)
    mgr_attrition = {}
    if cols.get("exited"):
        by_mgr = defaultdict(lambda: {"total": 0, "exits": 0})
        for e in emps:
            if e["manager"]:
                by_mgr[e["manager"]]["total"] += 1
                if e["exited"]:
                    by_mgr[e["manager"]]["exits"] += 1
        for m, v in by_mgr.items():
            mgr_attrition[m] = v["exits"] / v["total"] if v["total"] else 0

    # Score apenas para quem ainda está na empresa
    active = [e for e in emps if not e["exited"]]
    scored = []
    for e in active:
        s, factors = score_employee(e, mgr_attrition)
        scored.append({
            "name": e["name"], "area": e["area"], "manager": e["manager"] or "—",
            "level": e["level"] or "—", "score": s, "band": band(s),
            "factors": factors,
            "regretted_risk": band(s) in ("high", "critical") and e["performance"] is not None and e["performance"] >= 4,
            "performance": e["performance"],
        })
    scored.sort(key=lambda x: -x["score"])

    distribution = defaultdict(int)
    for s in scored:
        distribution[s["band"]] += 1

    at_risk = [s for s in scored if s["band"] in ("high", "critical")]
    regretted = [s for s in at_risk if s["regretted_risk"]]

    # Áreas e gestores mais quentes (média de score, min 1 pessoa)
    def hottest(key):
        agg = defaultdict(lambda: {"scores": [], "at_risk": 0})
        for s in scored:
            agg[s[key]]["scores"].append(s["score"])
            if s["band"] in ("high", "critical"):
                agg[s[key]]["at_risk"] += 1
        rows = [{"name": k, "hc": len(v["scores"]),
                 "avg_score": round(sum(v["scores"]) / len(v["scores"]), 1),
                 "at_risk": v["at_risk"]}
                for k, v in agg.items() if k and k != "—"]
        return sorted(rows, key=lambda x: -x["avg_score"])[:8]

    # Drivers agregados -> alavancas sugeridas
    driver_count = defaultdict(int)
    driver_points = defaultdict(float)
    for s in at_risk:
        for f in s["factors"]:
            driver_count[f["factor"]] += 1
            driver_points[f["factor"]] += f["points"]
    levers = sorted(
        [{"driver": d, "affected": driver_count[d],
          "total_points": round(driver_points[d], 1),
          "lever": LEVERS.get(d, "Conversa de retenção com o gestor")}
         for d in driver_count],
        key=lambda x: -x["total_points"])

    insights = []
    total = len(scored)
    if total == 0:
        insights.append("Nenhum colaborador pôde ser pontuado — confira as colunas do roster (precisa ao menos de name + 1 fator de risco).")
    else:
        pct = round(len(at_risk) / total * 100, 1)
        insights.append(f"<strong>{len(at_risk)}</strong> de {total} colaboradores ({pct}%) em risco alto ou crítico de saída.")
        if regretted:
            insights.append(f"<strong>{len(regretted)}</strong> em risco lamentável (regretted): alto risco E alto desempenho (4-5/5) — prioridade máxima.")
        if levers:
            top = levers[0]
            insights.append(f"Maior driver agregado: <strong>{_esc(top['driver'])}</strong> afetando {top['affected']} pessoa(s) em risco.")
        insights.append("Este score é um <strong>apoio ao planejamento</strong>, não um veredito. Use como gatilho pra conversas 1:1, nunca como decisão automática.")

    return {
        "summary": {
            "total_scored": total,
            "at_risk": len(at_risk),
            "regretted": len(regretted),
            "avg_score": round(sum(s["score"] for s in scored) / total, 1) if total else 0,
        },
        "distribution": {k: distribution[k] for k in ("low", "medium", "high", "critical")},
        "at_risk_list": at_risk[:50],
        "hottest_areas": hottest("area"),
        "hottest_managers": hottest("manager") if any(s["manager"] != "—" for s in scored) else [],
        "levers": levers,
        "insights": insights,
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>Flight Risk Forecast — Comp</title>
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
  .band-low{background:#d1fae5;color:#065f46}
  .band-medium{background:#fef3c7;color:#92400e}
  .band-high{background:#ffedd5;color:#9a3412}
  .band-critical{background:#fee2e2;color:#991b1b}
  .pill{display:inline-block;padding:.2rem .55rem;border-radius:999px;font-size:.7rem;font-weight:700}
  .fpill{display:inline-block;padding:.15rem .5rem;border-radius:6px;font-size:.7rem;font-weight:600;background:#f1f5f9;color:#334155;margin:.1rem .15rem .1rem 0}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-6xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Flight Risk Forecast</div>
<h1 class="text-3xl font-extrabold text-slate-900">Risco de saída — explicável, por colaborador</h1>
<p class="text-sm text-slate-500 mt-2" id="generated"></p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="card" style="background:#fff7ed;border:1px solid #fed7aa">
<p class="text-sm text-amber-800"><strong>Apoio ao planejamento, não veredito.</strong> Cada pontuação é explicável (fatores listados). Trate como gatilho pra conversas 1:1 com o gestor, nunca como decisão automática sobre pessoas.</p>
</div>

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
<div class="card"><div class="stat-label">Pontuados</div><div class="stat" id="s-total"></div></div>
<div class="card"><div class="stat-label">Em risco (alto+crítico)</div><div class="stat text-orange-600" id="s-risk"></div></div>
<div class="card"><div class="stat-label">Risco lamentável</div><div class="stat text-rose-600" id="s-reg"></div></div>
<div class="card"><div class="stat-label">Score médio</div><div class="stat" id="s-avg"></div></div>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Distribuição de risco</h2>
<div class="grid sm:grid-cols-4 gap-3" id="dist"></div>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Insights</h2>
<ul class="space-y-2" id="insights-list"></ul>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-1">Colaboradores em risco</h2>
<p class="text-xs text-slate-500 mb-4">Cada um mostra QUAIS fatores puxaram o score (transparência total).</p>
<div class="overflow-x-auto"><table><thead><tr><th>Nome</th><th>Área</th><th>Gestor</th><th>Score</th><th>Fatores que pesaram</th></tr></thead><tbody id="risk-tbody"></tbody></table></div>
</div>

<div class="grid sm:grid-cols-2 gap-6">
<div class="card"><h2 class="text-xl font-bold mb-4">Áreas mais quentes</h2><div class="overflow-x-auto"><table><thead><tr><th>Área</th><th>HC</th><th>Score médio</th><th>Em risco</th></tr></thead><tbody id="area-tbody"></tbody></table></div></div>
<div class="card" id="mgr-card"><h2 class="text-xl font-bold mb-4">Gestores mais quentes</h2><div class="overflow-x-auto"><table><thead><tr><th>Gestor</th><th>HC</th><th>Score médio</th><th>Em risco</th></tr></thead><tbody id="mgr-tbody"></tbody></table></div></div>
</div>

<div class="card" id="lever-card">
<h2 class="text-xl font-bold mb-4">Alavancas de retenção sugeridas</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Driver</th><th>Pessoas afetadas</th><th>Alavanca</th></tr></thead><tbody id="lever-tbody"></tbody></table></div>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=flight-risk-forecast" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });

document.getElementById('s-total').textContent = DATA.summary.total_scored;
document.getElementById('s-risk').textContent = DATA.summary.at_risk;
document.getElementById('s-reg').textContent = DATA.summary.regretted;
document.getElementById('s-avg').textContent = DATA.summary.avg_score;

const bandLabels = { low: 'Baixo (0-25)', medium: 'Médio (26-50)', high: 'Alto (51-75)', critical: 'Crítico (76-100)' };
const bandClass = { low: 'band-low', medium: 'band-medium', high: 'band-high', critical: 'band-critical' };
document.getElementById('dist').innerHTML = ['low','medium','high','critical'].map(k =>
  `<div class="${bandClass[k]} rounded-lg p-4 text-center">
    <div class="text-3xl font-bold">${DATA.distribution[k] || 0}</div>
    <div class="text-xs font-semibold mt-1">${bandLabels[k]}</div>
  </div>`).join('');

if (DATA.insights.length > 0) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li class="flex items-start"><span class="text-rose-500 font-bold mr-2">●</span><span>${i}</span></li>`).join('');
}

document.getElementById('risk-tbody').innerHTML = DATA.at_risk_list.map(s => {
  const fac = s.factors.map(f => `<span class="fpill">${esc(f.factor)} +${f.points}</span>`).join(' ');
  const reg = s.regretted_risk ? ' <span class="pill band-critical">lamentável</span>' : '';
  return `<tr>
    <td><strong>${esc(s.name)}</strong>${reg}</td>
    <td>${esc(s.area)}</td><td>${esc(s.manager)}</td>
    <td><span class="pill ${bandClass[s.band]}">${s.score}</span></td>
    <td>${fac || '<span class="text-slate-400">—</span>'}</td>
  </tr>`;
}).join('') || '<tr><td colspan="5" class="text-slate-400">Nenhum colaborador em risco alto ou crítico.</td></tr>';

document.getElementById('area-tbody').innerHTML = DATA.hottest_areas.map(a =>
  `<tr><td><strong>${esc(a.name)}</strong></td><td>${a.hc}</td><td>${a.avg_score}</td><td class="text-orange-600">${a.at_risk}</td></tr>`).join('');

if (DATA.hottest_managers.length > 0) {
  document.getElementById('mgr-tbody').innerHTML = DATA.hottest_managers.map(m =>
    `<tr><td><strong>${esc(m.name)}</strong></td><td>${m.hc}</td><td>${m.avg_score}</td><td class="text-orange-600">${m.at_risk}</td></tr>`).join('');
} else {
  document.getElementById('mgr-card').style.display = 'none';
}

if (DATA.levers.length > 0) {
  document.getElementById('lever-tbody').innerHTML = DATA.levers.map(l =>
    `<tr><td><strong>${esc(l.driver)}</strong></td><td>${l.affected}</td><td>${esc(l.lever)}</td></tr>`).join('');
} else {
  document.getElementById('lever-card').style.display = 'none';
}
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Scoring explicável de flight risk a partir de um roster CSV.")
    p.add_argument("--roster", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    headers, roster = load_csv(args.roster)
    cols = {k: auto_detect(headers, ROSTER_ALIASES, k) for k in ROSTER_ALIASES}
    if not cols.get("name"):
        sys.exit("Roster precisa ao menos da coluna name.")
    has_factor = any(cols.get(k) for k in ("comp_ratio", "salary", "promo", "engagement", "tenure"))
    if not has_factor:
        sys.exit("Roster precisa de ao menos um fator de risco: comp_ratio (ou salary+band_mid), engagement_score, months_since_last_promo ou tenure_months.")

    print(f"Roster: {len(roster)} linhas | colunas detectadas: " +
          ", ".join(f"{k}={v}" for k, v in cols.items() if v))
    data = analyze(roster, cols)
    out = args.output or Path.cwd() / f"flight-risk-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    print(f"  {data['summary']['total_scored']} pontuados | {data['summary']['at_risk']} em risco | {data['summary']['regretted']} risco lamentável")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=flight-risk-forecast")
    return 0


if __name__ == "__main__":
    sys.exit(main())
