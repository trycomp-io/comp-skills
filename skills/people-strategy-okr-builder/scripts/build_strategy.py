#!/usr/bin/env python3
"""
build_strategy.py — Renderiza um one-pager HTML da estratégia de People + OKRs
amarrados à estratégia de negócio, a partir de um JSON de estratégia.

Este script NÃO inventa conteúdo — ele renderiza o JSON que o agente monta
após coletar os inputs conversacionalmente (estratégia de negócio, dores de
people, contexto de headcount, horizonte, restrições).

Estrutura do JSON:

{
  "title": "People Strategy 2026",
  "owner": "CHRO",
  "horizon": "Anual",
  "business_context": "...",
  "priorities": [
    {
      "name": "Escalar engenharia sem perder qualidade de contratação",
      "business_goal": "Dobrar o time de produto no H2",
      "objective": "...",
      "key_results": [
        {"kr": "Reduzir time-to-hire de 60 para 35 dias", "target": "35 dias", "metric": "time-to-hire"}
      ],
      "initiatives": ["...", "..."],
      "owner": "Head de Talent",
      "metric": "time-to-hire"
    }
  ],
  "risks": ["..."],
  "dependencies": ["..."],
  "roadmap": [
    {"quarter": "Q1", "milestones": ["...", "..."]}
  ]
}

Uso:
    cat strategy.json | python3 build_strategy.py
    python3 build_strategy.py --input strategy.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "people-strategy-okr-builder"
SKILL_VERSION = "1.0.0"


def _slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip()).strip("-").lower()[:50] or "people-strategy"


def normalize(d):
    pr = d.get("priorities") or []
    for p in pr:
        p.setdefault("key_results", [])
        p.setdefault("initiatives", [])
        kr = p.get("key_results") or []
        for k in kr:
            if isinstance(k, str):
                continue
            k.setdefault("target", "")
            k.setdefault("metric", "")
    return {
        "title": d.get("title", "People Strategy"),
        "owner": d.get("owner", ""),
        "horizon": d.get("horizon", "Anual"),
        "business_context": d.get("business_context", ""),
        "priorities": pr,
        "risks": d.get("risks") or [],
        "dependencies": d.get("dependencies") or [],
        "roadmap": d.get("roadmap") or [],
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>People strategy · Zivo</title>
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
.priority{padding:24px 0;border-bottom:1px solid var(--zivo-ink-10)}
.priority:first-child{padding-top:0}
.priority:last-child{border-bottom:none;padding-bottom:0}
.priority-head{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap;margin-bottom:8px}
.priority-head h3{margin:0}
.owner{font-size:14px;line-height:20px;color:var(--zivo-ink-60);white-space:nowrap}
.goal{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;font-size:14px;line-height:20px;color:var(--zivo-ink-80);margin-bottom:8px}
.p-text{font-size:14px;line-height:20px;margin:0 0 8px}
.kr-label{margin:16px 0 4px}
.kr{display:flex;justify-content:space-between;gap:16px;align-items:baseline;padding:10px 0;border-bottom:1px solid var(--zivo-ink-10);font-size:14px;line-height:20px}
.kr-target{font-weight:700;white-space:nowrap;font-variant-numeric:tabular-nums}
.p-list{margin:4px 0 0;padding-left:20px;font-size:14px;line-height:20px}
.rail{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px}
.q{background:var(--zivo-white);border:1px solid var(--zivo-ink-10);border-top:1px solid var(--zivo-ink);padding:20px}
.q h3{margin-bottom:8px}
</style></head>
<body>

<header class="hero">
<div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>People strategy</span><span id="horizon"></span><span id="generated"></span></div>
<h1 id="title"></h1>
<p class="hero-sub">Owner: <span id="owner"></span>. Prioridades de People e OKRs amarrados à estratégia de negócio.</p>
</div>
</header>

<main class="page">

<section class="section" id="ctx-card" style="display:none;">
<div class="callout"><div class="label">Contexto de negócio</div><p id="ctx" style="margin-top:8px"></p></div>
</section>

<section class="section">
<h2>Prioridades estratégicas</h2>
<div class="card"><div id="priorities"></div></div>
</section>

<section class="section">
<div class="grid-2">
<div id="risks-card" style="display:none;"><h2>Riscos</h2><div class="card"><ul class="p-list" id="risks"></ul></div></div>
<div id="deps-card" style="display:none;"><h2>Dependências</h2><div class="card"><ul class="p-list" id="deps"></ul></div></div>
</div>
</section>

<section class="section" id="roadmap-card" style="display:none;">
<h2>Roadmap trimestral</h2>
<div class="rail" id="roadmap"></div>
</section>

</main>

<footer class="site-footer">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=people-strategy-okr-builder" aria-label="Zivo"><svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg></a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer>

<script>
const DATA = __DATA__;
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
document.getElementById('generated').textContent = new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'short', year:'numeric' });
document.getElementById('title').textContent = DATA.title;
document.getElementById('owner').textContent = DATA.owner || '—';
document.getElementById('horizon').textContent = 'Horizonte: ' + (DATA.horizon || 'Anual');

if (DATA.business_context) {
  document.getElementById('ctx-card').style.display = '';
  document.getElementById('ctx').textContent = DATA.business_context;
}

document.getElementById('priorities').innerHTML = DATA.priorities.map((p, i) => {
  const krs = (p.key_results || []).map(k => {
    if (typeof k === 'string') return `<div class="kr"><span>${esc(k)}</span></div>`;
    const tgt = k.target ? `<span class="kr-target">${esc(k.target)}</span>` : '';
    return `<div class="kr"><span>${esc(k.kr || '')}${k.metric ? ` <span class="muted">(${esc(k.metric)})</span>` : ''}</span>${tgt}</div>`;
  }).join('');
  const inits = (p.initiatives || []).length
    ? `<div class="p-text" style="margin-top:12px"><strong>Iniciativas</strong><ul class="p-list">${p.initiatives.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>` : '';
  return `<div class="priority">
    <div class="priority-head">
      <h3>${i + 1}. ${esc(p.name || '')}</h3>
      ${p.owner ? `<span class="owner">Owner: <strong>${esc(p.owner)}</strong></span>` : ''}
    </div>
    ${p.business_goal ? `<div class="goal"><span class="badge">Negócio</span> <span>${esc(p.business_goal)}</span></div>` : ''}
    ${p.objective ? `<p class="p-text"><strong>Objetivo:</strong> ${esc(p.objective)}</p>` : ''}
    <div class="label kr-label">Key results</div>
    ${krs}
    ${inits}
    ${p.metric ? `<p class="p-text muted" style="margin-top:8px">Métrica-chave: <strong>${esc(p.metric)}</strong></p>` : ''}
  </div>`;
}).join('');

if (DATA.risks.length) { document.getElementById('risks-card').style.display = ''; document.getElementById('risks').innerHTML = DATA.risks.map(r => `<li>${esc(r)}</li>`).join(''); }
if (DATA.dependencies.length) { document.getElementById('deps-card').style.display = ''; document.getElementById('deps').innerHTML = DATA.dependencies.map(r => `<li>${esc(r)}</li>`).join(''); }

if (DATA.roadmap.length) {
  document.getElementById('roadmap-card').style.display = '';
  document.getElementById('roadmap').innerHTML = DATA.roadmap.map(q =>
    `<div class="q"><h3><i class="zv-dot"></i>${esc(q.quarter || '')}</h3><ul class="p-list">${(q.milestones || []).map(m => `<li>${esc(m)}</li>`).join('')}</ul></div>`).join('');
}
</script>
</body></html>
"""


def render_html(data, out):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Renderiza one-pager HTML de estratégia de People + OKRs.")
    p.add_argument("--input", type=Path, help="JSON de estratégia (senão, lê do stdin)")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    if args.input:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        if sys.stdin.isatty():
            sys.exit("Forneça --input <file> ou pipe o JSON de estratégia via stdin.")
        raw = json.loads(sys.stdin.read())

    data = normalize(raw)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = args.output or Path.cwd() / f"people-strategy-{_slug(data['title'])}-{ts}.html"
    render_html(data, out)
    print(f"Gerado: {out}")
    print(f"  {len(data['priorities'])} prioridade(s) estratégica(s)")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=people-strategy-okr-builder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
