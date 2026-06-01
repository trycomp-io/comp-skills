#!/usr/bin/env python3
"""
recruiting_funnel.py — Efetividade de aquisição de talentos. A partir de um CSV
de pipeline de candidatos, calcula conversão estágio-a-estágio, time-to-fill /
tempo em estágio, taxa de aceite de oferta + motivos de recusa, efetividade por
fonte, e o gargalo (estágio de menor pass-through).

Input pipeline CSV:
  candidate_id/name, role/req (opt), source (opt),
  stage_reached (applied/screen/interview/offer/hired) OU outcome
  (hired/rejected/declined), applied_date + hired_date (opt), decline_reason (opt)

Output: HTML com funil, tabela de conversão, métricas de tempo, ROI por fonte,
callout de gargalo.

Uso:
    python3 recruiting_funnel.py --pipeline pipeline.csv
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

SKILL_NAME = "recruiting-funnel-analytics"
SKILL_VERSION = "1.0.0"

# ordem canônica do funil
STAGES = ["applied", "screen", "interview", "offer", "hired"]
STAGE_LABELS = {
    "applied": "Aplicações", "screen": "Triagem", "interview": "Entrevista",
    "offer": "Oferta", "hired": "Contratado",
}

ALIASES = {
    "id":            ["candidate_id", "candidate", "candidato", "id", "name", "nome"],
    "role":          ["role", "req", "vaga", "position", "cargo", "requisicao", "requisição", "job"],
    "source":        ["source", "fonte", "canal", "origin", "origem"],
    "stage":         ["stage_reached", "stage", "estagio", "estágio", "etapa", "fase"],
    "outcome":       ["outcome", "resultado", "status", "disposition"],
    "applied_date":  ["applied_date", "data_aplicacao", "data_aplicação", "application_date", "data_inscricao"],
    "hired_date":    ["hired_date", "data_contratacao", "data_contratação", "hire_date", "start_date", "data_admissao"],
    "decline_reason":["decline_reason", "motivo_recusa", "motivo", "reason", "decline"],
}

# mapeia valores de stage_reached -> índice canônico
STAGE_MAP = {
    "applied": 0, "application": 0, "aplicado": 0, "aplicacao": 0, "inscrito": 0, "novo": 0,
    "screen": 1, "screening": 1, "triagem": 1, "phone_screen": 1, "rh": 1,
    "interview": 2, "entrevista": 2, "tech_interview": 2, "onsite": 2, "painel": 2, "loop": 2,
    "offer": 3, "oferta": 3, "proposta": 3,
    "hired": 4, "hire": 4, "contratado": 4, "admitido": 4, "fechado": 4, "accepted": 4,
}
OUTCOME_HIRED = {"hired", "hire", "contratado", "admitido", "accepted", "aceito", "fechado"}
OUTCOME_DECLINED = {"declined", "decline", "recusou", "recusado", "desistiu", "withdrew", "withdrawn"}


def _esc(v):
    import html
    return html.escape(str(v), quote=True) if v is not None else ""


def _norm(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii").strip().lower().replace(" ", "_")


def auto_detect(headers, key):
    h = {_norm(x): x for x in headers}
    for cand in ALIASES[key]:
        if _norm(cand) in h:
            return h[_norm(cand)]
    return None


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def _val(row, col):
    return ((row.get(col) or "").strip() if col else "") or None


def _date(s):
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def stage_index(row, cols):
    """Retorna o índice do estágio mais avançado atingido pelo candidato."""
    # outcome=hired sempre conta como hired
    outc = _norm(_val(row, cols.get("outcome")) or "")
    if outc in OUTCOME_HIRED:
        return 4
    st = _norm(_val(row, cols.get("stage")) or "")
    if st in STAGE_MAP:
        idx = STAGE_MAP[st]
        # se outcome diz declined num offer, ainda atingiu offer (não hired)
        if idx == 4 and outc in OUTCOME_DECLINED:
            return 3
        return idx
    # sem stage explícito: se tem applied_date, ao menos aplicou
    if _val(row, cols.get("applied_date")) or _val(row, cols.get("id")):
        return 0
    return None


def analyze(rows, cols):
    has_stage = bool(cols.get("stage")) or bool(cols.get("outcome"))
    has_source = bool(cols.get("source"))
    has_dates = bool(cols.get("applied_date")) and bool(cols.get("hired_date"))

    # contagem "atingiu pelo menos o estágio i"
    reached = [0] * len(STAGES)
    candidates = []
    for row in rows:
        idx = stage_index(row, cols)
        if idx is None:
            continue
        for i in range(idx + 1):
            reached[i] += 1
        candidates.append({"row": row, "idx": idx})

    # conversão estágio-a-estágio
    funnel = []
    for i, st in enumerate(STAGES):
        n = reached[i]
        prev = reached[i - 1] if i > 0 else None
        passthrough = round(n / prev * 100, 1) if (prev and prev > 0) else (100.0 if i == 0 else None)
        funnel.append({"stage": st, "label": STAGE_LABELS[st], "count": n, "passthrough": passthrough})

    # gargalo = menor pass-through entre estágios 1..4
    bottleneck = None
    cand_pt = [(f["stage"], f["passthrough"]) for f in funnel[1:] if f["passthrough"] is not None]
    if cand_pt:
        b = min(cand_pt, key=lambda x: x[1])
        bottleneck = {"stage": b[0], "label": STAGE_LABELS[b[0]], "passthrough": b[1],
                      "from_label": STAGE_LABELS[STAGES[STAGES.index(b[0]) - 1]]}

    # aceite de oferta + motivos de recusa
    offers = reached[3]
    hires = reached[4]
    offer_accept = round(hires / offers * 100, 1) if offers > 0 else None
    decline_reasons = defaultdict(int)
    declined_total = 0
    for c in candidates:
        outc = _norm(_val(c["row"], cols.get("outcome")) or "")
        if outc in OUTCOME_DECLINED or (c["idx"] == 3 and outc in OUTCOME_DECLINED):
            declined_total += 1
            dr = _val(c["row"], cols.get("decline_reason"))
            decline_reasons[dr or "Não informado"] += 1
    decline_rows = sorted(({"reason": k, "count": v} for k, v in decline_reasons.items()),
                          key=lambda x: -x["count"])

    # time-to-fill (média de dias entre applied e hired, só dos contratados com ambas datas)
    ttf_days = []
    if has_dates:
        for c in candidates:
            if c["idx"] != 4:
                continue
            ad = _date(_val(c["row"], cols.get("applied_date")))
            hd = _date(_val(c["row"], cols.get("hired_date")))
            if ad and hd and hd >= ad:
                ttf_days.append((hd - ad).days)
    avg_ttf = round(sum(ttf_days) / len(ttf_days), 1) if ttf_days else None
    median_ttf = None
    if ttf_days:
        sd = sorted(ttf_days)
        m = len(sd) // 2
        median_ttf = sd[m] if len(sd) % 2 else round((sd[m - 1] + sd[m]) / 2, 1)

    # efetividade por fonte
    by_source = []
    if has_source:
        srcs = defaultdict(lambda: {"applied": 0, "hired": 0})
        for c in candidates:
            s = _val(c["row"], cols.get("source")) or "Não informado"
            srcs[s]["applied"] += 1
            if c["idx"] == 4:
                srcs[s]["hired"] += 1
        by_source = sorted([
            {"source": s, "applied": v["applied"], "hired": v["hired"],
             "conversion": round(v["hired"] / v["applied"] * 100, 1) if v["applied"] else 0.0}
            for s, v in srcs.items()
        ], key=lambda x: (-x["hired"], -x["conversion"]))

    insights = []
    total = len(candidates)
    if total == 0:
        insights.append("Nenhum candidato pôde ser analisado — verifique stage_reached/outcome ou as datas.")
    else:
        overall_conv = round(hires / reached[0] * 100, 1) if reached[0] else None
        insights.append(f"<strong>{total}</strong> candidatos no pipeline · {hires} contratado(s) · conversão geral applied→hired: <strong>{overall_conv}%</strong>.")
        if bottleneck:
            insights.append(f"Gargalo no funil: <strong>{_esc(bottleneck['from_label'])} → {_esc(bottleneck['label'])}</strong> com apenas <strong>{bottleneck['passthrough']}%</strong> de pass-through.")
        if offer_accept is not None:
            insights.append(f"Taxa de aceite de oferta: <strong>{offer_accept}%</strong> ({hires}/{offers}).")
            if offer_accept < 80 and offers >= 3:
                insights.append("Aceite de oferta abaixo de 80% — investigar competitividade de proposta e experiência do candidato.")
        if avg_ttf is not None:
            insights.append(f"Time-to-fill médio: <strong>{avg_ttf} dias</strong> (mediana {median_ttf}).")
        if by_source:
            best = by_source[0]
            insights.append(f"Fonte com mais contratações: <strong>{_esc(best['source'])}</strong> ({best['hired']} hires, {best['conversion']}% de conversão).")

    return {
        "summary": {
            "total": total,
            "hired": hires,
            "offers": offers,
            "offer_accept": offer_accept,
            "avg_ttf": avg_ttf,
            "median_ttf": median_ttf,
            "has_source": has_source,
            "has_dates": has_dates,
        },
        "funnel": funnel,
        "bottleneck": bottleneck,
        "decline_reasons": decline_rows,
        "declined_total": declined_total,
        "by_source": by_source,
        "insights": insights,
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>Recruiting Funnel Analytics — Comp</title>
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
  .fbar{background:#ff4456;color:white;border-radius:8px;padding:.75rem 1rem;display:flex;justify-content:space-between;align-items:center;margin:0 auto;font-weight:600}
  .pt{display:inline-block;font-size:.75rem;color:#64748b;font-weight:600}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-6xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Recruiting Funnel Analytics</div>
<h1 class="text-3xl font-extrabold text-slate-900">Efetividade de recrutamento</h1>
<p class="text-sm text-slate-500 mt-2" id="generated"></p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
<div class="card"><div class="stat-label">Candidatos</div><div class="stat" id="s-total"></div></div>
<div class="card"><div class="stat-label">Contratados</div><div class="stat text-emerald-600" id="s-hired"></div></div>
<div class="card"><div class="stat-label">Aceite de oferta</div><div class="stat" id="s-accept"></div></div>
<div class="card"><div class="stat-label">Time-to-fill (média)</div><div class="stat text-rose-600" id="s-ttf"></div></div>
</div>

<div class="card">
<h2 class="text-xl font-bold mb-4">Funil de conversão</h2>
<div id="funnel" class="space-y-3"></div>
</div>

<div class="card" id="bottleneck-card" style="display:none;background:#fff7ed;border:1px solid #fed7aa;">
<h2 class="text-lg font-bold mb-1 text-orange-800">Gargalo do funil</h2>
<p class="text-sm text-orange-900" id="bottleneck-text"></p>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2 class="text-xl font-bold mb-4">Insights</h2>
<ul class="space-y-2" id="insights-list"></ul>
</div>

<div class="grid sm:grid-cols-2 gap-6">
<div class="card" id="source-card" style="display:none;"><h2 class="text-xl font-bold mb-4">Efetividade por fonte</h2><div class="overflow-x-auto"><table><thead><tr><th>Fonte</th><th>Aplicações</th><th>Hires</th><th>Conversão</th></tr></thead><tbody id="source-tbody"></tbody></table></div></div>
<div class="card" id="decline-card" style="display:none;"><h2 class="text-xl font-bold mb-4">Motivos de recusa</h2><div class="overflow-x-auto"><table><thead><tr><th>Motivo</th><th>Qtd</th></tr></thead><tbody id="decline-tbody"></tbody></table></div></div>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=recruiting-funnel-analytics" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });
const pct = v => (v === null || v === undefined) ? '—' : v + '%';

document.getElementById('s-total').textContent = DATA.summary.total;
document.getElementById('s-hired').textContent = DATA.summary.hired;
document.getElementById('s-accept').textContent = pct(DATA.summary.offer_accept);
document.getElementById('s-ttf').textContent = DATA.summary.avg_ttf === null ? '—' : DATA.summary.avg_ttf + 'd';

const maxN = Math.max(...DATA.funnel.map(f => f.count), 1);
document.getElementById('funnel').innerHTML = DATA.funnel.map(f => {
  const w = Math.max(12, Math.round(f.count / maxN * 100));
  const ptxt = f.passthrough === null ? '' : `<span class="pt ml-3">${f.passthrough}% pass-through</span>`;
  return `<div class="flex items-center gap-3">
    <div style="width:${w}%"><div class="fbar"><span>${esc(f.label)}</span><span>${f.count}</span></div></div>
    ${ptxt}
  </div>`;
}).join('');

if (DATA.bottleneck) {
  document.getElementById('bottleneck-card').style.display = '';
  document.getElementById('bottleneck-text').innerHTML = `Menor pass-through em <strong>${esc(DATA.bottleneck.from_label)} → ${esc(DATA.bottleneck.label)}</strong>: apenas <strong>${DATA.bottleneck.passthrough}%</strong> avançam. Priorize melhorias nesse estágio.`;
}

if (DATA.insights.length > 0) {
  document.getElementById('insights-card').style.display = '';
  document.getElementById('insights-list').innerHTML = DATA.insights.map(i =>
    `<li class="flex items-start"><span class="text-rose-500 font-bold mr-2">●</span><span>${i}</span></li>`).join('');
}

if (DATA.by_source.length > 0) {
  document.getElementById('source-card').style.display = '';
  document.getElementById('source-tbody').innerHTML = DATA.by_source.map(s =>
    `<tr><td><strong>${esc(s.source)}</strong></td><td>${s.applied}</td><td>${s.hired}</td><td>${s.conversion}%</td></tr>`).join('');
}

if (DATA.decline_reasons.length > 0) {
  document.getElementById('decline-card').style.display = '';
  document.getElementById('decline-tbody').innerHTML = DATA.decline_reasons.map(d =>
    `<tr><td>${esc(d.reason)}</td><td>${d.count}</td></tr>`).join('');
}
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Analytics do funil de recrutamento.")
    p.add_argument("--pipeline", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--stage-col"); p.add_argument("--outcome-col"); p.add_argument("--source-col")
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    headers, rows = load_csv(args.pipeline)
    cols = {k: auto_detect(headers, k) for k in ALIASES}
    if args.stage_col: cols["stage"] = args.stage_col
    if args.outcome_col: cols["outcome"] = args.outcome_col
    if args.source_col: cols["source"] = args.source_col
    if not cols.get("stage") and not cols.get("outcome"):
        sys.exit("Pipeline precisa de stage_reached OU outcome (hired/rejected/declined). Verifique colunas.")

    print(f"Pipeline: {len(rows)} linhas | stage='{cols.get('stage')}' outcome='{cols.get('outcome')}' source='{cols.get('source')}'")
    data = analyze(rows, cols)
    out = args.output or Path.cwd() / f"recruiting-funnel-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    bn = data["bottleneck"]
    print(f"  {data['summary']['total']} candidatos | {data['summary']['hired']} hires" + (f" | gargalo: {bn['from_label']}→{bn['label']} ({bn['passthrough']}%)" if bn else ""))

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=recruiting-funnel-analytics")
    return 0


if __name__ == "__main__":
    sys.exit(main())
