#!/usr/bin/env python3
"""
render_pack.py — Renderiza pacote defensável de comp budget pra CHRO levar
ao CFO/CEO. Estrutura cada linha do pedido (% reajuste, novas vagas, ajustes
pontuais) com justificativa, benchmark, custo total e cenários alternativos.

Schema JSON:
{
  "period": "H2 2026",
  "ask_summary": "Pedido total de R$ X em comp/headcount no H2",
  "total_request_brl": 1500000,
  "current_payroll_brl_monthly": 800000,
  "items": [
    {
      "category": "reajuste|hire|adjustment",
      "label": "Reajuste de mérito 5% no time de Eng",
      "rationale": "Inflação 4%, mercado Eng pagando +15% acima da empresa, retenção em risco",
      "benchmark_source": "Robert Half / Mercer",
      "headcount_affected": 30,
      "cost_monthly": 24000,
      "cost_annual_loaded": 449000
    }
  ],
  "scenarios": [
    {"name": "Pedido completo", "cost": 1500000, "outcome": "..."},
    {"name": "50% do pedido", "cost": 750000, "outcome": "..."}
  ],
  "risks_if_denied": ["..."],
  "asks_decision": "Aprovar R$ X até DATA"
}

Uso:
    cat pack.json | python3 render_pack.py
"""

from __future__ import annotations

import argparse, json, re, sys, unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "comp-budget-defense-pack"
SKILL_VERSION = "1.0.0"


def _slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip()).strip("-").lower()[:50] or "pack"


def _esc(s):
    if s is None: return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _money(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "—"


CAT_LABELS = {"reajuste": ("Reajuste", "bg-amber-100 text-amber-800"),
              "hire": ("Hire", "bg-blue-100 text-blue-800"),
              "adjustment": ("Ajuste pontual", "bg-purple-100 text-purple-800")}


HTML = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>Comp Budget Defense Pack — {period}</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  body{{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b}}
  .card{{background:white;border-radius:12px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin-bottom:1.5rem}}
  h1{{font-size:2rem;font-weight:800;color:#0f172a}}
  h2{{font-size:1.25rem;font-weight:700;color:#0f172a;margin-bottom:1rem;border-bottom:2px solid #f1f5f9;padding-bottom:.5rem}}
  .stat{{font-size:2.25rem;font-weight:800}}
  .stat-label{{font-size:.875rem;color:#64748b;text-transform:uppercase;font-weight:600}}
  table{{width:100%;border-collapse:collapse;font-size:.85rem}}
  th{{background:#1e293b;color:white;padding:.65rem;text-align:left;font-size:.75rem;text-transform:uppercase}}
  td{{padding:.65rem;border-bottom:1px solid #e2e8f0;vertical-align:top}}
  .pill{{display:inline-block;padding:.2rem .6rem;border-radius:999px;font-size:.7rem;font-weight:600}}
  .ask{{background:#fef3c7;border-left:4px solid #f59e0b;padding:1.25rem;border-radius:0 8px 8px 0;font-weight:600;font-size:1.05rem}}
  .risk{{background:#fee2e2;border-left:4px solid #dc2626;padding:.75rem 1rem;border-radius:0 8px 8px 0;margin-bottom:.5rem}}
  .scenario{{border:1px solid #e2e8f0;border-radius:8px;padding:1rem;margin-bottom:.75rem}}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-5xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Comp Budget Defense Pack</div>
<h1>{period}</h1>
<p class="text-slate-600 mt-2">{ask_summary}</p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-6">
<div class="card"><div class="stat-label">Pedido total</div><div class="stat text-rose-600">{total_request}</div></div>
<div class="card"><div class="stat-label">Folha atual (mensal)</div><div class="stat">{current_payroll}</div></div>
<div class="card"><div class="stat-label">% impacto na folha</div><div class="stat">{pct_impact}</div></div>
</div>

<div class="card">
<h2>Linhas do pedido (justificadas)</h2>
<div class="overflow-x-auto"><table><thead><tr><th>Categoria</th><th>Item</th><th>HC</th><th>Mensal</th><th>Anual c/ encargos</th><th>Justificativa</th></tr></thead><tbody>
{items_html}
</tbody></table></div>
</div>

<div class="card">
<h2>Cenários</h2>
{scenarios_html}
</div>

{risks_html}

<div class="card">
<h2>Ask</h2>
<div class="ask">{asks_decision}</div>
</div>

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=comp-budget-defense-pack" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div></body></html>
"""


def render_html(d):
    period = _esc(d.get("period", ""))
    ask_summary = _esc(d.get("ask_summary", ""))
    total_request = _money(d.get("total_request_brl"))
    current_payroll = _money(d.get("current_payroll_brl_monthly"))
    pct_impact = "—"
    try:
        if d.get("current_payroll_brl_monthly") and d.get("total_request_brl"):
            pct_impact = f"{(float(d['total_request_brl']) / (float(d['current_payroll_brl_monthly']) * 12) * 100):.1f}%"
    except (TypeError, ValueError):
        pass

    items_html = []
    for it in d.get("items", []):
        cat = it.get("category", "")
        label, cls = CAT_LABELS.get(cat, (cat or "—", "bg-slate-100 text-slate-800"))
        bench = f' <span class="text-xs text-slate-500">({_esc(it.get("benchmark_source"))})</span>' if it.get("benchmark_source") else ""
        items_html.append(
            f"<tr>"
            f'<td><span class="pill {cls}">{label}</span></td>'
            f"<td><strong>{_esc(it.get('label'))}</strong></td>"
            f"<td>{_esc(it.get('headcount_affected', '—'))}</td>"
            f"<td>{_money(it.get('cost_monthly'))}</td>"
            f"<td>{_money(it.get('cost_annual_loaded'))}</td>"
            f"<td>{_esc(it.get('rationale'))}{bench}</td>"
            f"</tr>"
        )

    scenarios_html = []
    for s in d.get("scenarios", []):
        scenarios_html.append(
            f'<div class="scenario">'
            f'<div class="flex justify-between items-start">'
            f'<div><strong>{_esc(s.get("name"))}</strong>'
            f'<div class="text-sm text-slate-600 mt-1">{_esc(s.get("outcome"))}</div></div>'
            f'<div class="text-lg font-bold text-rose-600">{_money(s.get("cost"))}</div>'
            f'</div></div>'
        )

    risks_html = ""
    if d.get("risks_if_denied"):
        risks_html = '<div class="card"><h2>Riscos se negado</h2>' + \
                     "".join(f'<div class="risk">{_esc(r)}</div>' for r in d["risks_if_denied"]) + \
                     '</div>'

    return HTML.format(
        period=period, ask_summary=ask_summary,
        total_request=total_request, current_payroll=current_payroll, pct_impact=pct_impact,
        items_html="\n".join(items_html) or '<tr><td colspan="6">—</td></tr>',
        scenarios_html="\n".join(scenarios_html),
        risks_html=risks_html,
        asks_decision=_esc(d.get("asks_decision", "")),
    )


def main():
    p = argparse.ArgumentParser(description="Renderiza Comp Budget Defense Pack.")
    p.add_argument("--input", type=Path); p.add_argument("--output", type=Path)
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    if args.input:
        d = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        if sys.stdin.isatty(): sys.exit("Forneça --input <file> ou pipe JSON via stdin.")
        d = json.loads(sys.stdin.read())

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = _slug(d.get("period", "pack"))
    out = args.output or Path.cwd() / f"comp-budget-pack-{slug}-{ts}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(d), encoding="utf-8")
    print(f"Gerado: {out}")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass
    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=comp-budget-defense-pack")
    return 0


if __name__ == "__main__":
    sys.exit(main())
