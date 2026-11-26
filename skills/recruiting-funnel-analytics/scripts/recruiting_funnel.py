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
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Recruiting Funnel Analytics · Zivo</title>
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
  .fbar{background:#1A1A1A;color:#FFFFFF;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:14px;line-height:20px;font-weight:700;white-space:nowrap}
  .fbar.hl{background:#F4364C}
  .pt{display:inline-block;font-size:12px;line-height:16px;color:rgba(26,26,26,.6);font-weight:700;white-space:nowrap}
  @media (max-width:560px){#funnel>div{flex-wrap:wrap;row-gap:4px}#funnel>div>div{min-width:max-content}#funnel .pt{margin-left:0}}
</style></head>
<body>
<header class="hero"><div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>Recruiting funnel</span><span><span id="generated"></span></span><span>Confidencial</span></div>
<h1>Efetividade de recrutamento</h1>
<p class="hero-sub">Conversão estágio a estágio, tempo até a contratação, aceite de oferta e retorno por fonte.</p>
</div></header>
<main class="page">

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
<div class="card"><div class="stat-label">Candidatos</div><div class="stat" id="s-total"></div></div>
<div class="card"><div class="stat-label">Contratados</div><div class="stat" id="s-hired"></div></div>
<div class="card"><div class="stat-label">Aceite de oferta</div><div class="stat" id="s-accept"></div></div>
<div class="card"><div class="stat-label">Time-to-fill (média)</div><div class="stat" id="s-ttf"></div></div>
</div>

<div class="card">
<h2>Funil de conversão</h2>
<div id="funnel" class="space-y-3"></div>
</div>

<div class="card" id="bottleneck-card" style="display:none;">
<h2 style="margin-bottom:8px">Gargalo do funil <span class="badge badge-warn" style="vertical-align:4px;margin-left:8px">Atenção</span></h2>
<p class="text-sm" id="bottleneck-text"></p>
</div>

<div class="card" id="insights-card" style="display:none;">
<h2>Insights</h2>
<ul class="space-y-2 zv-list" id="insights-list"></ul>
</div>

<div class="grid sm:grid-cols-2 gap-6">
<div class="card" id="source-card" style="display:none;"><h2>Efetividade por fonte</h2><div class="overflow-x-auto"><table><thead><tr><th>Fonte</th><th>Aplicações</th><th>Hires</th><th>Conversão</th></tr></thead><tbody id="source-tbody"></tbody></table></div></div>
<div class="card" id="decline-card" style="display:none;"><h2>Motivos de recusa</h2><div class="overflow-x-auto"><table><thead><tr><th>Motivo</th><th>Qtd</th></tr></thead><tbody id="decline-tbody"></tbody></table></div></div>
</div>

</main>
<footer class="site-footer">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=recruiting-funnel-analytics" aria-label="Zivo"><svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg></a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer>

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
    <div style="width:${w}%"><div class="fbar${DATA.bottleneck && f.label === DATA.bottleneck.label ? ' hl' : ''}"><span>${esc(f.label)}</span><span>${f.count}</span></div></div>
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
    `<li class="flex items-start"><i class="zv-dot"></i><span>${i}</span></li>`).join('');
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
    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=recruiting-funnel-analytics")
    return 0


if __name__ == "__main__":
    sys.exit(main())
