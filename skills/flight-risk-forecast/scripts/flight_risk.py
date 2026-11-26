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
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Flight risk forecast · Zivo</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Marcellus&family=Source+Sans+3:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<style>
:root {
  --zivo-ink: #1A1A1A;
  --zivo-off-white: #F1F1EA;
  --zivo-white: #FFFFFF;
  --zivo-red: #F4364C;
  --zivo-red-hover: #E02A40;
  --zivo-red-pressed: #9E1528;
  --zivo-ink-80: rgba(26,26,26,.8);
  --zivo-ink-60: rgba(26,26,26,.6);
  --zivo-ink-40: rgba(26,26,26,.4);
  --zivo-ink-30: rgba(26,26,26,.3);
  --zivo-ink-20: rgba(26,26,26,.2);
  --zivo-ink-10: rgba(26,26,26,.1);
  --zivo-ink-05: rgba(26,26,26,.05);
  --zivo-success: #0B7A43; --zivo-success-bg: #DDF7EA; --zivo-success-fill: #12B76A;
  --zivo-warning: #985704; --zivo-warning-bg: #FFF2DA; --zivo-warning-fill: #F69B10;
  --zivo-error: #B3172A;   --zivo-error-bg: #FEE7EA;   --zivo-error-fill: #D61F35;
  --zivo-info: #0B58BB;    --zivo-info-bg: #E7F1FF;    --zivo-info-fill: #1C7CE5;
  --zivo-font-flare: "ABC Arizona Flare", Marcellus, Georgia, serif;
  --zivo-font-sans: "ABC Arizona Sans", "Source Sans 3", system-ui, -apple-system, "Segoe UI", sans-serif;
  --zivo-radius: 0;
  --gap: 24px;
}

* { box-sizing: border-box; border-radius: 0; box-shadow: none; }

body {
  margin: 0;
  font-family: var(--zivo-font-sans);
  font-size: 16px;
  line-height: 1.5;
  color: var(--zivo-ink);
  background: var(--zivo-off-white);
  -webkit-font-smoothing: antialiased;
}

h1, h2, h3, h4 {
  font-family: var(--zivo-font-flare);
  font-weight: 400;
  font-style: normal;
  text-transform: none;
  margin: 0 0 .4em;
}
h1 { font-size: 56px; line-height: 54px; letter-spacing: -0.02em; }
h2 { font-size: 32px; line-height: 36px; letter-spacing: -0.01em; }
h3 { font-size: 22px; line-height: 28px; }
h4 { font-size: 18px; line-height: 24px; }
p { margin: 0 0 1em; }
small, .small { font-size: 14px; line-height: 20px; }
.caption, .label {
  font-size: 12px; line-height: 16px; text-transform: uppercase;
  letter-spacing: .04em; color: var(--zivo-ink-60);
}
.muted { color: var(--zivo-ink-60); }
a { color: var(--zivo-ink); text-decoration: underline; text-underline-offset: 2px; }
a:hover { color: var(--zivo-ink-80); }

/* Square node / overline marker */
.zv-dot { display: inline-block; width: 8px; height: 8px; background: currentColor; margin-right: 8px; vertical-align: 1px; }
.zv-dot--red { background: var(--zivo-red); }

/* Header row: four captions over a 1px rule */
.zv-header-row {
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--gap);
  padding-bottom: 10px; margin-bottom: 40px;
  border-bottom: 1px solid var(--zivo-ink-30);
  font-size: 12px; line-height: 16px; text-transform: uppercase; letter-spacing: .04em;
}

/* Hero */
.hero { background: var(--zivo-ink); color: var(--zivo-white); padding: 32px 0 48px; }
.hero-inner { max-width: 1120px; margin: 0 auto; padding: 0 32px; }
.hero .zv-header-row { border-bottom-color: rgba(255,255,255,.3); color: rgba(255,255,255,.8); }
.hero h1 { color: var(--zivo-white); max-width: 22ch; }
.hero-sub { margin: 16px 0 0; color: rgba(255,255,255,.7); font-family: var(--zivo-font-flare); font-size: 22px; line-height: 28px; max-width: 60ch; }
.logo-tile { width: 56px; height: 56px; display: grid; place-items: center; background: var(--zivo-white); color: var(--zivo-ink); font-family: var(--zivo-font-flare); font-size: 28px; }
.logo-tile img { max-width: 44px; max-height: 44px; }

/* Page */
.page { max-width: 1120px; margin: 0 auto; padding: 48px 32px; }
.section { margin-bottom: 48px; }
.section > h2 { margin-bottom: 16px; }

/* Cards */
.card { background: var(--zivo-white); border: 1px solid var(--zivo-ink-10); padding: 24px; }
.card + .card { margin-top: var(--gap); }
.card h3 { margin-bottom: 12px; }

/* Stat strip */
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
.stat-card { background: var(--zivo-white); border: 1px solid var(--zivo-ink-10); padding: 20px; }
.stat-card .value { font-family: var(--zivo-font-flare); font-size: 40px; line-height: 44px; margin-top: 8px; font-variant-numeric: tabular-nums; }
.stat-card .value.accent { color: var(--zivo-red); }
.stat-card .context { font-size: 14px; line-height: 20px; color: var(--zivo-ink-80); margin-top: 8px; }
.trend-up { color: var(--zivo-success); }
.trend-down { color: var(--zivo-error); }
.trend-flat { color: var(--zivo-ink-60); }

/* Big number: one per page */
.big-number .value { font-family: var(--zivo-font-flare); font-size: 96px; line-height: 92px; letter-spacing: -0.02em; }
.big-number .rule { height: 1px; background: var(--zivo-ink); margin: 16px 0; }
.big-number .label { font-size: 22px; line-height: 28px; text-transform: none; letter-spacing: 0; color: var(--zivo-ink); }

/* Tables */
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; line-height: 20px; background: var(--zivo-white); }
thead th {
  text-align: left; font-weight: 700; font-size: 12px; line-height: 16px;
  text-transform: uppercase; letter-spacing: .04em; color: var(--zivo-ink-80);
  border-bottom: 1px solid var(--zivo-ink-30); padding: 10px 12px;
}
tbody td { padding: 10px 12px; border-bottom: 1px solid var(--zivo-ink-10); vertical-align: top; }
tbody tr:last-child td { border-bottom: none; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }

/* Buttons: square, one arrow */
.btn {
  display: inline-block; padding: 12px 16px; font-family: var(--zivo-font-sans); font-size: 16px; line-height: 20px;
  background: var(--zivo-ink); color: var(--zivo-white); border: 1px solid var(--zivo-ink);
  text-decoration: none; cursor: pointer;
}
.btn:hover { background: #333; color: var(--zivo-white); }
.btn-secondary { background: transparent; color: var(--zivo-ink); }
.btn-secondary:hover { background: var(--zivo-ink-05); color: var(--zivo-ink); }
.btn-primary { background: var(--zivo-red); border-color: var(--zivo-red); color: var(--zivo-white); }
.btn-primary:hover { background: var(--zivo-red-hover); border-color: var(--zivo-red-hover); }
.btn-primary:active { background: var(--zivo-red-pressed); }

/* Badges: the only rounded element */
.badge { display: inline-block; white-space: nowrap; padding: 2px 10px; border-radius: 999px; font-size: 12px; line-height: 18px; font-weight: 700; background: var(--zivo-ink-05); color: var(--zivo-ink); }
.badge-good { background: var(--zivo-success-bg); color: var(--zivo-success); }
.badge-warn { background: var(--zivo-warning-bg); color: var(--zivo-warning); }
.badge-bad  { background: var(--zivo-error-bg);   color: var(--zivo-error); }
.badge-info { background: var(--zivo-info-bg);    color: var(--zivo-info); }

/* Meters */
.meter { height: 8px; background: var(--zivo-ink-10); }
.meter > span { display: block; height: 100%; background: var(--zivo-ink); }

/* Callout: neutral note, no coloured side borders */
.callout { background: var(--zivo-white); border-top: 1px solid var(--zivo-ink); padding: 16px 0 0; }

/* Footer */
.site-footer {
  max-width: 1120px; margin: 0 auto; padding: 24px 32px 40px;
  display: flex; align-items: center; gap: 24px; flex-wrap: wrap;
  border-top: 1px solid var(--zivo-ink-10);
  font-size: 14px; line-height: 20px; color: var(--zivo-ink-60);
}
.site-footer a { color: inherit; }
.zv-wordmark { display: inline-flex; line-height: 0; }
.zv-wordmark svg { height: 20px; width: auto; }

@media (max-width: 560px) {
  .hero-inner, .page, .site-footer { padding-left: 20px; padding-right: 20px; }
  h1, .hero h1 { font-size: 36px; line-height: 36px; }
  h2 { font-size: 26px; line-height: 30px; }
  .zv-header-row { grid-template-columns: repeat(2, minmax(0, 1fr)); row-gap: 8px; }
  .big-number .value { font-size: 64px; line-height: 64px; }
}

@media print {
  body { background: var(--zivo-white); }
  .hero { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}

/* Report components */
.grid-2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:24px;align-items:start}
.grid-2 > .card + .card{margin-top:0}
.section-sub{font-size:14px;line-height:20px;color:var(--zivo-ink-60);margin:-8px 0 16px}
.insights{list-style:none;margin:0;padding:0}
.insights li{display:flex;align-items:flex-start;padding:10px 0;border-bottom:1px solid var(--zivo-ink-10)}
.insights li:first-child{padding-top:0}
.insights li:last-child{border-bottom:none;padding-bottom:0}
.insights .zv-dot{flex:none;margin-top:8px}
.hero .zv-header-row span{min-width:0;overflow-wrap:anywhere}
.callout{padding:16px 20px;border-bottom:1px solid var(--zivo-ink-10)}
.callout p:last-child{margin-bottom:0}
@media (max-width:560px){.stat-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.stat-card .value{font-size:32px;line-height:36px}}
td.num,th.num{white-space:nowrap}
@media (max-width:560px){.card{padding:16px}.stat-card .value{font-size:28px;line-height:32px;overflow-wrap:anywhere}}
.factors{display:flex;flex-wrap:wrap;gap:4px}
</style></head>
<body>

<header class="hero">
<div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>Flight risk</span><span id="generated"></span><span>Confidencial</span></div>
<h1>Risco de saída explicável, por colaborador</h1>
<p class="hero-sub">Cada ponto de risco vem de um fator transparente: comp, carreira, engajamento, tempo de casa e gestor.</p>
</div>
</header>

<main class="page">

<section class="section">
<div class="callout"><p class="small"><strong>Apoio ao planejamento, não veredito.</strong> Cada pontuação é explicável (fatores listados). Trate como gatilho pra conversas 1:1 com o gestor, nunca como decisão automática sobre pessoas.</p></div>
</section>

<section class="section">
<div class="stat-grid">
<div class="stat-card"><div class="label">Pontuados</div><div class="value" id="s-total"></div><div class="context">Colaboradores ativos no roster.</div></div>
<div class="stat-card"><div class="label">Em risco (alto + crítico)</div><div class="value" id="s-risk"></div><div class="context">Score acima de 50.</div></div>
<div class="stat-card"><div class="label">Risco lamentável</div><div class="value accent" id="s-reg"></div><div class="context">Alto risco e desempenho 4-5/5.</div></div>
<div class="stat-card"><div class="label">Score médio</div><div class="value" id="s-avg"></div><div class="context">Escala de 0 a 100.</div></div>
</div>
</section>

<section class="section">
<h2>Distribuição de risco</h2>
<div class="stat-grid" id="dist"></div>
</section>

<section class="section" id="insights-card" style="display:none;">
<h2>Insights</h2>
<div class="card"><ul class="insights" id="insights-list"></ul></div>
</section>

<section class="section">
<h2>Colaboradores em risco</h2>
<p class="section-sub">Cada linha mostra quais fatores puxaram o score.</p>
<div class="card table-wrap"><table><thead><tr><th>Nome</th><th>Área</th><th>Gestor</th><th class="num">Score</th><th>Fatores que pesaram</th></tr></thead><tbody id="risk-tbody"></tbody></table></div>
</section>

<section class="section">
<div class="grid-2">
<div><h2>Áreas mais quentes</h2><div class="card table-wrap"><table><thead><tr><th>Área</th><th class="num">HC</th><th class="num">Score médio</th><th class="num">Em risco</th></tr></thead><tbody id="area-tbody"></tbody></table></div></div>
<div id="mgr-card"><h2>Gestores mais quentes</h2><div class="card table-wrap"><table><thead><tr><th>Gestor</th><th class="num">HC</th><th class="num">Score médio</th><th class="num">Em risco</th></tr></thead><tbody id="mgr-tbody"></tbody></table></div></div>
</div>
</section>

<section class="section" id="lever-card">
<h2>Alavancas de retenção sugeridas</h2>
<div class="card table-wrap"><table><thead><tr><th>Driver</th><th class="num">Pessoas afetadas</th><th>Alavanca</th></tr></thead><tbody id="lever-tbody"></tbody></table></div>
</section>

</main>

<footer class="site-footer">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=flight-risk-forecast" aria-label="Zivo"><svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg></a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'short', year:'numeric' });

document.getElementById('s-total').textContent = DATA.summary.total_scored;
document.getElementById('s-risk').textContent = DATA.summary.at_risk;
document.getElementById('s-reg').textContent = DATA.summary.regretted;
document.getElementById('s-avg').textContent = DATA.summary.avg_score;

const bandLabels = { low: 'Baixo (0-25)', medium: 'Médio (26-50)', high: 'Alto (51-75)', critical: 'Crítico (76-100)' };
const bandClass = { low: 'badge-good', medium: '', high: 'badge-warn', critical: 'badge-bad' };
const bandName = { low: 'Baixo', medium: 'Médio', high: 'Alto', critical: 'Crítico' };
document.getElementById('dist').innerHTML = ['low','medium','high','critical'].map(k =>
  `<div class="stat-card">
    <div class="label">${bandLabels[k]}</div>
    <div class="value">${DATA.distribution[k] || 0}</div>
    <div class="context"><span class="badge ${bandClass[k]}">${bandName[k]}</span></div>
  </div>`).join('');

if (DATA.insights.length > 0) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li><i class="zv-dot"></i><span>${i}</span></li>`).join('');
}

document.getElementById('risk-tbody').innerHTML = DATA.at_risk_list.map(s => {
  const fac = s.factors.map(f => `<span class="badge">${esc(f.factor)} +${f.points}</span>`).join('');
  const reg = s.regretted_risk ? ' <span class="badge badge-bad">lamentável</span>' : '';
  return `<tr>
    <td><strong>${esc(s.name)}</strong>${reg}</td>
    <td>${esc(s.area)}</td><td>${esc(s.manager)}</td>
    <td class="num"><span class="badge ${bandClass[s.band]}">${s.score}</span></td>
    <td>${fac ? '<div class="factors">' + fac + '</div>' : '<span class="muted">—</span>'}</td>
  </tr>`;
}).join('') || '<tr><td colspan="5" class="muted">Nenhum colaborador em risco alto ou crítico.</td></tr>';

document.getElementById('area-tbody').innerHTML = DATA.hottest_areas.map(a =>
  `<tr><td><strong>${esc(a.name)}</strong></td><td class="num">${a.hc}</td><td class="num">${a.avg_score}</td><td class="num">${a.at_risk}</td></tr>`).join('');

if (DATA.hottest_managers.length > 0) {
  document.getElementById('mgr-tbody').innerHTML = DATA.hottest_managers.map(m =>
    `<tr><td><strong>${esc(m.name)}</strong></td><td class="num">${m.hc}</td><td class="num">${m.avg_score}</td><td class="num">${m.at_risk}</td></tr>`).join('');
} else {
  document.getElementById('mgr-card').style.display = 'none';
}

if (DATA.levers.length > 0) {
  document.getElementById('lever-tbody').innerHTML = DATA.levers.map(l =>
    `<tr><td><strong>${esc(l.driver)}</strong></td><td class="num">${l.affected}</td><td>${esc(l.lever)}</td></tr>`).join('');
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
    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=flight-risk-forecast")
    return 0


if __name__ == "__main__":
    sys.exit(main())
