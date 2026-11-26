#!/usr/bin/env python3
"""
total_comp.py — Calculadora de Total Compensation (modelo Zivo).

Monta o pacote completo de remuneração: salário base + benefícios + variável
(bonus/ICP) + equity (SOP/ILP com cenários de exit). Produz 2 headline numbers
(near-term e long-term) + breakdown detalhado + visão visual HTML.

Estrutura baseada no modelo de Total Comp da Zivo:
- Near-term (cash + benefícios + variável)
- Long-term (cash + benefícios + ICP + ILP no cenário target)

Uso:
    python3 total_comp.py \\
        --base-mensal 12900 --meses 13.33 \\
        --bonus-salarios 2.5 \\
        --beneficios "Ticket:1356,Plano de Saúde:635" \\
        --sop-shares 1500 --sop-strike 1.12 --sop-pps 4.15 \\
        --sop-vesting 4 --sop-cliff 1 --fx 5.20 \\
        --cenarios "Base:5,Target:10,Homerun:30" \\
        --output html
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "total-comp-calculator"
SKILL_VERSION = "1.0.0"

# Default: 12 meses + 13º + 1/3 férias ≈ 13,33
DEFAULT_MESES = 13.33


def fmt_brl(v: float) -> str:
    s = f"{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def fmt_usd(v: float) -> str:
    return f"$ {v:,.2f}"


def parse_beneficios(s: str | None) -> list[dict]:
    """'Ticket:1356,Plano de Saúde:635' → [{'name':..., 'monthly':...}]"""
    if not s:
        return []
    out = []
    for part in s.split(","):
        if ":" not in part:
            continue
        name, val = part.rsplit(":", 1)
        try:
            out.append({"name": name.strip(), "monthly": float(val.strip().replace(".", "").replace(",", "."))})
        except ValueError:
            continue
    return out


def parse_cenarios(s: str | None) -> list[dict]:
    """'Base:5,Target:10,Homerun:30' → [{'name':'Base','mult':5}, ...]"""
    if not s:
        return [{"name": "Base", "mult": 5}, {"name": "Target", "mult": 10}, {"name": "Homerun", "mult": 30}]
    out = []
    for part in s.split(","):
        if ":" not in part:
            continue
        name, mult = part.rsplit(":", 1)
        try:
            out.append({"name": name.strip(), "mult": float(mult.strip())})
        except ValueError:
            continue
    return out or [{"name": "Base", "mult": 5}, {"name": "Target", "mult": 10}, {"name": "Homerun", "mult": 30}]


def compute(args) -> dict:
    base_mensal = args.base_mensal
    meses = args.meses
    base_anual = round(base_mensal * meses, 2)

    # Variável / bonus
    if args.bonus_salarios is not None:
        bonus_anual = round(base_mensal * args.bonus_salarios, 2)
    elif args.bonus_pct is not None:
        bonus_anual = round(base_anual * args.bonus_pct / 100, 2)
    elif args.bonus_absoluto is not None:
        bonus_anual = round(args.bonus_absoluto, 2)
    else:
        bonus_anual = 0.0

    total_cash_anual = round(base_anual + bonus_anual, 2)

    # Benefícios
    beneficios = parse_beneficios(args.beneficios)
    benef_mensal = sum(b["monthly"] for b in beneficios)
    benef_anual = round(benef_mensal * 12, 2)

    total_cash_benef_anual = round(total_cash_anual + benef_anual, 2)

    # SOP / ILP
    sop = None
    cenarios_out = []
    ilp_target_anual = 0.0
    if args.sop_shares and args.sop_pps:
        shares = args.sop_shares
        pps = args.sop_pps
        strike = args.sop_strike or 0.0
        vesting = args.sop_vesting or 4
        fx = args.fx or 5.0
        net_of_strike = args.sop_net_of_strike

        # Valor gross hoje (USD): shares × pps (usa gross)
        gross_usd = round(shares * pps, 2)

        cenarios = parse_cenarios(args.cenarios)
        for c in cenarios:
            mult = c["mult"]
            if net_of_strike:
                # exit pps = pps × mult; net per share = (exit_pps - strike)
                per_share_usd = (pps * mult) - strike
            else:
                per_share_usd = pps * mult
            total_usd = shares * per_share_usd
            total_brl = round(total_usd * fx, 2)
            anual_brl = round(total_brl / vesting, 2)
            cenarios_out.append({
                "name": c["name"],
                "mult": mult,
                "total_brl": total_brl,
                "anual_brl": anual_brl,
                "total_cash_stocks_anual": round(total_cash_anual + anual_brl, 2),
            })

        # ILP pro headline long-term = cenário "Target" (ou o 2º, ou mediano)
        target = next((x for x in cenarios_out if x["name"].lower() == "target"), None)
        if not target and len(cenarios_out) >= 2:
            target = cenarios_out[len(cenarios_out) // 2]
        elif not target and cenarios_out:
            target = cenarios_out[0]
        ilp_target_anual = target["anual_brl"] if target else 0.0

        sop = {
            "shares": shares, "strike_usd": strike, "pps_usd": pps,
            "vesting_years": vesting, "cliff_years": args.sop_cliff or 1,
            "fx": fx, "gross_usd": gross_usd, "net_of_strike": net_of_strike,
            "target_name": target["name"] if target else None,
        }

    # Headlines
    total_comp_near = round(base_anual + benef_anual + bonus_anual, 2)
    total_comp_long = round(base_anual + benef_anual + bonus_anual + ilp_target_anual, 2)

    return {
        "inputs": {
            "base_mensal": base_mensal, "meses": meses,
            "bonus_anual": bonus_anual,
        },
        "cash": {
            "base_mensal": base_mensal,
            "base_anual": base_anual,
            "bonus_anual": bonus_anual,
            "total_cash_anual": total_cash_anual,
            "base_mensal_com_beneficios": round(base_mensal + benef_mensal, 2),
        },
        "beneficios": {
            "items": beneficios,
            "mensal": round(benef_mensal, 2),
            "anual": benef_anual,
        },
        "total_cash_benef_anual": total_cash_benef_anual,
        "sop": sop,
        "cenarios": cenarios_out,
        "ilp_target_anual": ilp_target_anual,
        "headline": {
            "near_term": total_comp_near,
            "long_term": total_comp_long,
            "near_label": "Salário base + benefícios + remuneração variável",
            "long_label": "Salário base + benefícios + ICP + ILP (cenário target)",
        },
    }


# ========== CLI output (Cowork-friendly markdown) ==========


def print_result(r: dict) -> None:
    h = r["headline"]
    print()
    print("=" * 64)
    print("  TOTAL COMPENSATION")
    print("=" * 64)
    print(f"  TOTAL COMP (long-term):  {fmt_brl(h['long_term'])}/ano")
    print(f"    {h['long_label']}")
    print(f"  TOTAL COMP (near-term):  {fmt_brl(h['near_term'])}/ano")
    print(f"    {h['near_label']}")
    print()

    c = r["cash"]
    print("  CASH")
    print("  " + "-" * 56)
    print(f"    Salário base mensal:          {fmt_brl(c['base_mensal'])}")
    print(f"    Salário base anual:           {fmt_brl(c['base_anual'])}")
    print(f"    Bônus anual:                  {fmt_brl(c['bonus_anual'])}")
    print(f"    Total Cash anual:             {fmt_brl(c['total_cash_anual'])}")
    print(f"    Base mensal + benefícios:     {fmt_brl(c['base_mensal_com_beneficios'])}")
    print()

    b = r["beneficios"]
    if b["items"]:
        print("  BENEFÍCIOS (mensal)")
        print("  " + "-" * 56)
        for item in b["items"]:
            print(f"    {item['name']:<28} {fmt_brl(item['monthly'])}")
        print(f"    {'Sub-total mensal':<28} {fmt_brl(b['mensal'])}")
        print(f"    {'Anual (× 12)':<28} {fmt_brl(b['anual'])}")
        print()

    if r["sop"]:
        s = r["sop"]
        print("  SOP / ILP (equity)")
        print("  " + "-" * 56)
        print(f"    Strike: {fmt_usd(s['strike_usd'])} · PPS: {fmt_usd(s['pps_usd'])} · Ações: {int(s['shares']):,}".replace(",", "."))
        print(f"    Vesting: {s['vesting_years']} anos · Cliff: {s['cliff_years']} ano(s) · FX: {s['fx']}")
        print(f"    Valor gross hoje: {fmt_usd(s['gross_usd'])}" + ("" if not s['net_of_strike'] else " (cenários líquidos de strike)"))
        print()
        print("  CENÁRIOS DE EXIT")
        print("  " + "-" * 56)
        print(f"    {'Cenário':<12} {'Múlt':>5} {'Total R$':>16} {'Anual R$':>14} {'Cash+Stock/ano':>18}")
        for c2 in r["cenarios"]:
            print(f"    {c2['name']:<12} {c2['mult']:>4g}x {fmt_brl(c2['total_brl']):>16} {fmt_brl(c2['anual_brl']):>14} {fmt_brl(c2['total_cash_stocks_anual']):>18}")
        print()


# ========== HTML visual analysis ==========


def render_html(r: dict, output: Path) -> None:
    h = r["headline"]
    c = r["cash"]
    b = r["beneficios"]
    sop = r["sop"]

    benef_rows = "".join(
        f"<tr><td>{_esc(i['name'])}</td><td>{fmt_brl(i['monthly'])}</td></tr>" for i in b["items"]
    )
    cenario_rows = "".join(
        f"<tr><td><strong>{_esc(c2['name'])}</strong></td><td>{c2['mult']:g}x</td>"
        f"<td>{fmt_brl(c2['total_brl'])}</td><td>{fmt_brl(c2['anual_brl'])}</td>"
        f"<td><strong>{fmt_brl(c2['total_cash_stocks_anual'])}</strong></td></tr>"
        for c2 in r["cenarios"]
    )

    # Composition for the long-term stacked bar
    comp_base = c["base_anual"]
    comp_benef = b["anual"]
    comp_bonus = c["bonus_anual"]
    comp_ilp = r["ilp_target_anual"]
    total_long = h["long_term"] or 1
    def pct(x): return round(x / total_long * 100, 1)

    sop_block = ""
    if sop:
        sop_block = f"""
    <div class="card">
      <h2>SOP / ILP (equity)</h2>
      <div class="sop-meta">
        <span>Strike: {fmt_usd(sop['strike_usd'])}</span>
        <span>PPS: {fmt_usd(sop['pps_usd'])}</span>
        <span>Ações: {int(sop['shares']):,}</span>
        <span>Vesting: {sop['vesting_years']}a</span>
        <span>Cliff: {sop['cliff_years']}a</span>
        <span>FX: {sop['fx']}</span>
      </div>
      <div class="overflow-x-auto"><table>
        <thead><tr><th>Cenário</th><th>Múlt.</th><th>Total R$</th><th>Anual R$</th><th>Total Cash + Stocks/ano</th></tr></thead>
        <tbody>{cenario_rows}</tbody>
      </table></div>
      <p class="note">Valor {'líquido de strike' if sop['net_of_strike'] else 'gross (não deduz strike)'}. Anual = total ÷ {sop['vesting_years']} anos de vesting. ILP no headline usa o cenário <strong>{_esc(sop['target_name'] or 'Target')}</strong>.</p>
    </div>""".replace(",", ".") if sop else ""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Total Compensation · Zivo</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<!-- Zivo theme for pages built with the Tailwind CDN.
     Paste right after <script src="https://cdn.tailwindcss.com/3.4.16"></script>.
     Square radii, no shadows, Zivo tokens and fonts. See references/style-guide.md §8. -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Marcellus&family=Source+Sans+3:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<script>
tailwind.config = {{
  theme: {{
    borderRadius: {{ none: '0', sm: '0', DEFAULT: '0', md: '0', lg: '0', xl: '0', '2xl': '0', '3xl': '0', full: '9999px' }},
    boxShadow: {{ sm: 'none', DEFAULT: 'none', md: 'none', lg: 'none', xl: 'none', '2xl': 'none', inner: 'none', none: 'none' }},
    fontFamily: {{
      display: ['"ABC Arizona Flare"', 'Marcellus', 'Georgia', 'serif'],
      sans: ['"ABC Arizona Sans"', '"Source Sans 3"', 'system-ui', 'sans-serif'],
    }},
    extend: {{
      colors: {{
        zv: {{
          ink: '#1A1A1A', off: '#F1F1EA', white: '#FFFFFF',
          red: '#F4364C', 'red-hover': '#E02A40', 'red-pressed': '#9E1528',
          ink80: 'rgba(26,26,26,.8)', ink60: 'rgba(26,26,26,.6)', ink40: 'rgba(26,26,26,.4)',
          ink30: 'rgba(26,26,26,.3)', ink20: 'rgba(26,26,26,.2)', line: 'rgba(26,26,26,.1)', ink05: 'rgba(26,26,26,.05)',
          success: '#0B7A43', 'success-bg': '#DDF7EA', 'success-fill': '#12B76A',
          warning: '#985704', 'warning-bg': '#FFF2DA', 'warning-fill': '#F69B10',
          error: '#B3172A', 'error-bg': '#FEE7EA', 'error-fill': '#D61F35',
          info: '#0B58BB', 'info-bg': '#E7F1FF', 'info-fill': '#1C7CE5',
          indigo: '#4636F2', aqua: '#12C3C9', orchid: '#C24BE6', citron: '#D4E030', midnight: '#1F188C',
        }},
      }},
    }},
  }},
}};
</script>
<style>
  body {{ font-family: "ABC Arizona Sans", "Source Sans 3", system-ui, sans-serif; background: #F1F1EA; color: #1A1A1A; }}
  h1, h2, h3, h4, .font-display {{ font-family: "ABC Arizona Flare", Marcellus, Georgia, serif; font-weight: 400 !important; font-style: normal; text-transform: none; }}
  h1 {{ letter-spacing: -0.02em; }}
  h2 {{ letter-spacing: -0.01em; }}
  a {{ text-underline-offset: 2px; }}
  .zv-dot {{ display: inline-block; width: 8px; height: 8px; background: currentColor; margin-right: 8px; vertical-align: 1px; }}
  .zv-dot--red {{ background: #F4364C; }}
  .zv-caption {{ font-size: 12px; line-height: 16px; text-transform: uppercase; letter-spacing: .04em; }}
  .zv-wordmark {{ display: inline-flex; line-height: 0; }}
  .zv-wordmark svg {{ height: 20px; width: auto; }}
  .tabular {{ font-variant-numeric: tabular-nums; }}
</style>
<style>
  *,::before,::after{{border-radius:0;box-shadow:none}}
  body{{margin:0;background:#F1F1EA;color:#1A1A1A;font-size:16px;line-height:1.5;-webkit-font-smoothing:antialiased}}
  .hero{{background:#1A1A1A;color:#FFFFFF;padding:32px 0 48px}}
  .hero-inner{{max-width:1120px;margin:0 auto;padding:0 32px}}
  .zv-header-row{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:24px;padding-bottom:10px;margin-bottom:40px;border-bottom:1px solid rgba(255,255,255,.3);color:rgba(255,255,255,.8);font-size:12px;line-height:16px;text-transform:uppercase;letter-spacing:.04em}}
  .hero h1{{font-size:56px;line-height:54px;color:#FFFFFF;max-width:22ch;margin:0}}
  .hero-sub{{margin:16px 0 0;color:rgba(255,255,255,.7);font-family:"ABC Arizona Flare",Marcellus,Georgia,serif;font-size:22px;line-height:28px;max-width:60ch}}
  .hero-sub a{{color:#FFFFFF;text-decoration:underline;text-underline-offset:2px}}
  .page{{max-width:1120px;margin:0 auto;padding:48px 32px}}
  .page a{{color:#1A1A1A;text-decoration:underline;text-underline-offset:2px}}
  .card{{background:#FFFFFF;border:1px solid rgba(26,26,26,.1);padding:24px;margin-bottom:24px;min-width:0}}
  .card h2{{font-size:22px;line-height:28px;margin-bottom:16px}}
  .stat{{font-family:"ABC Arizona Flare",Marcellus,Georgia,serif;font-size:40px;line-height:44px;margin-top:8px;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}}
  .stat.accent{{color:#F4364C}}
  .stat-label{{font-size:12px;line-height:16px;text-transform:uppercase;letter-spacing:.04em;color:rgba(26,26,26,.6)}}
  .page table{{width:100%;border-collapse:collapse;font-size:14px;line-height:20px;background:#FFFFFF}}
  .page th{{text-align:left;font-weight:700;font-size:12px;line-height:16px;text-transform:uppercase;letter-spacing:.04em;color:rgba(26,26,26,.8);background:#FFFFFF;border-bottom:1px solid rgba(26,26,26,.3);padding:10px 12px}}
  .page td{{padding:10px 12px;border-bottom:1px solid rgba(26,26,26,.1);vertical-align:top;font-variant-numeric:tabular-nums}}
  .page tbody tr:last-child td{{border-bottom:none}}
  .badge,.pill{{display:inline-block;white-space:nowrap;padding:2px 10px;border-radius:999px;font-family:"ABC Arizona Sans","Source Sans 3",system-ui,sans-serif;font-size:12px;line-height:18px;font-weight:700;background:rgba(26,26,26,.05);color:#1A1A1A}}
  .badge-good{{background:#DDF7EA;color:#0B7A43}}.badge-warn{{background:#FFF2DA;color:#985704}}
  .badge-bad{{background:#FEE7EA;color:#B3172A}}.badge-info{{background:#E7F1FF;color:#0B58BB}}
  .st-good{{color:#0B7A43;font-weight:700}}.st-warn{{color:#985704;font-weight:700}}.st-bad{{color:#B3172A;font-weight:700}}
  .zv-list li{{display:flex;align-items:flex-start}}
  .zv-list .zv-dot{{flex:none;margin-top:8px}}
  .site-footer{{max-width:1120px;margin:0 auto;padding:24px 32px 40px;display:flex;align-items:center;gap:24px;flex-wrap:wrap;border-top:1px solid rgba(26,26,26,.1);font-size:14px;line-height:20px;color:rgba(26,26,26,.6)}}
  .site-footer a{{color:inherit}}
  @media (max-width:560px){{
    .hero-inner,.page,.site-footer{{padding-left:20px;padding-right:20px}}
    .hero h1{{font-size:36px;line-height:36px}}
    .zv-header-row{{grid-template-columns:repeat(2,minmax(0,1fr));row-gap:8px}}
    .stat{{font-size:32px;line-height:36px}}
    .card{{padding:16px}}
    .page th,.page td{{padding:8px 6px}}
  }}
  .headline{{background:#FFFFFF;border:1px solid rgba(26,26,26,.1);padding:24px;display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:16px}}
  .headline-label{{font-size:12px;line-height:16px;text-transform:uppercase;letter-spacing:.04em;color:rgba(26,26,26,.6);font-weight:700}}
  .headline-sub{{font-size:14px;line-height:20px;color:rgba(26,26,26,.8);margin-top:4px}}
  .headline-val{{font-family:"ABC Arizona Flare",Marcellus,Georgia,serif;font-size:40px;line-height:44px;font-variant-numeric:tabular-nums}}
  .headline-val.accent{{color:#F4364C}}
  .sop-meta{{display:flex;flex-wrap:wrap;gap:8px 24px;font-size:14px;color:rgba(26,26,26,.8);margin-bottom:16px}}
  .note{{font-size:14px;line-height:20px;color:rgba(26,26,26,.6);margin-top:12px}}
  .bar{{display:flex;height:40px;overflow:hidden;margin:16px 0}}
  .seg-base{{background:#1A1A1A}}.seg-benef{{background:#4636F2}}.seg-bonus{{background:#12C3C9}}.seg-ilp{{background:#C24BE6}}
  .legend{{display:flex;flex-wrap:wrap;gap:16px;font-size:14px}}
  .legend span{{display:flex;align-items:center;gap:6px}}
  .dot{{width:12px;height:12px;display:inline-block}}
</style></head>
<body>
<header class="hero"><div class="hero-inner">
<div class="zv-header-row"><span><i class="zv-dot zv-dot--red"></i>Zivo</span><span>Total compensation</span><span>Gerado em {datetime.now().strftime('%d/%m/%Y')}</span><span>Confidencial</span></div>
<h1>Pacote de remuneração</h1>
<p class="hero-sub">Cash, benefícios, variável e equity somados em dois headline numbers.</p>
</div></header>
<main class="page">

<div class="headline">
  <div><div class="headline-label">Total comp (long-term, anual)</div><div class="headline-sub">{_esc(h['long_label'])}</div></div>
  <div class="headline-val accent">{fmt_brl(h['long_term'])}</div>
</div>
<div class="headline">
  <div><div class="headline-label">Total comp (near-term, anual)</div><div class="headline-sub">{_esc(h['near_label'])}</div></div>
  <div class="headline-val">{fmt_brl(h['near_term'])}</div>
</div>

<div class="card">
<h2>Composição (long-term)</h2>
<div class="bar">
  <div class="seg-base" style="width:{pct(comp_base)}%" title="Base"></div>
  <div class="seg-benef" style="width:{pct(comp_benef)}%" title="Benefícios"></div>
  <div class="seg-bonus" style="width:{pct(comp_bonus)}%" title="Bônus"></div>
  <div class="seg-ilp" style="width:{pct(comp_ilp)}%" title="ILP"></div>
</div>
<div class="legend">
  <span><span class="dot seg-base"></span> Base {pct(comp_base)}%</span>
  <span><span class="dot seg-benef"></span> Benefícios {pct(comp_benef)}%</span>
  <span><span class="dot seg-bonus"></span> Variável/ICP {pct(comp_bonus)}%</span>
  <span><span class="dot seg-ilp"></span> ILP/Equity {pct(comp_ilp)}%</span>
</div>
</div>

<div class="card">
<h2>Cash</h2>
<div class="overflow-x-auto"><table>
<tbody>
<tr><td>Salário base mensal</td><td>{fmt_brl(c['base_mensal'])}</td></tr>
<tr><td>Salário base anual</td><td>{fmt_brl(c['base_anual'])}</td></tr>
<tr><td>Bônus anual</td><td>{fmt_brl(c['bonus_anual'])}</td></tr>
<tr><td><strong>Total Cash anual</strong></td><td><strong>{fmt_brl(c['total_cash_anual'])}</strong></td></tr>
<tr><td>Base mensal + benefícios</td><td>{fmt_brl(c['base_mensal_com_beneficios'])}</td></tr>
</tbody>
</table></div>
</div>

<div class="card">
<h2>Benefícios</h2>
<table>
<thead><tr><th>Benefício</th><th>Mensal</th></tr></thead>
<tbody>{benef_rows}
<tr><td><strong>Sub-total mensal</strong></td><td><strong>{fmt_brl(b['mensal'])}</strong></td></tr>
<tr><td>Anual (× 12)</td><td>{fmt_brl(b['anual'])}</td></tr>
</tbody>
</table>
</div>

{sop_block}

</main>
<footer class="site-footer">
<a class="zv-wordmark" href="https://zivo.ai?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=total-comp-calculator" aria-label="Zivo"><svg role="img" aria-label="Zivo" xmlns="http://www.w3.org/2000/svg" viewBox="1.0000 0.4375 273.6250 64.9800" width="273.625" height="64.980"><path d="M172.992 52.6741L150.676 1.50781H139.883L166.523 64.3458H179.47L206.2 1.50781H195.406L172.992 52.6741Z" fill="#1A1A1A"/><path d="M241.983 0.4375C223.549 0.4375 209.332 14.4387 209.332 32.9272C209.332 51.4158 223.541 65.417 241.983 65.417C260.425 65.417 274.535 51.4158 274.625 32.9272C274.535 14.4387 260.417 0.4375 241.983 0.4375ZM241.983 55.7314C229.208 55.7314 219.585 46.0376 219.585 32.9354C219.585 19.8333 229.208 10.1395 241.983 10.1395C254.758 10.1395 264.282 19.8333 264.282 32.9354C264.282 46.0376 254.66 55.7314 241.983 55.7314Z" fill="#1A1A1A"/><path d="M73.4883 1.50781V11.2016H96.5167V54.6521H73.4883V64.3458H129.7V54.6521H106.68V11.2016H129.7V1.50781H73.4883Z" fill="#1A1A1A"/><path d="M1 1.50781V11.2016H7.85446H44.4362L1 54.6521V64.3458H52.56H57.2115V54.6521H52.56H13.6853L57.2115 11.2016V1.50781H7.85446H1Z" fill="#1A1A1A"/></svg></a>
<span>Powered by Zivo · free skills for HR &amp; People leaders</span>
</footer></body></html>
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")


def _esc(s):
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ========== CLI ==========


def main() -> int:
    p = argparse.ArgumentParser(description="Calculadora de Total Compensation (modelo Zivo).")
    p.add_argument("--base-mensal", type=float, required=True, help="Salário base mensal (R$)")
    p.add_argument("--meses", type=float, default=DEFAULT_MESES, help="Multiplicador anual (default 13,33 = 12+13º+1/3 férias)")
    # Bonus — uma das 3 formas
    p.add_argument("--bonus-salarios", type=float, help="Bônus em nº de salários (ex: 2.5)")
    p.add_argument("--bonus-pct", type=float, help="Bônus como %% do salário base anual")
    p.add_argument("--bonus-absoluto", type=float, help="Bônus anual em valor absoluto (R$)")
    # Benefícios
    p.add_argument("--beneficios", help="'Nome:valor_mensal,Nome2:valor2' (ex: 'Ticket:1356,Plano de Saúde:635')")
    # SOP / ILP
    p.add_argument("--sop-shares", type=float, help="Nº de ações (SOP)")
    p.add_argument("--sop-strike", type=float, help="Strike price (USD)")
    p.add_argument("--sop-pps", type=float, help="Price per share atual / última rodada (USD)")
    p.add_argument("--sop-vesting", type=int, default=4, help="Anos de vesting (default 4)")
    p.add_argument("--sop-cliff", type=int, default=1, help="Cliff em anos (default 1)")
    p.add_argument("--sop-net-of-strike", action="store_true", help="Deduz strike no cenário (mais conservador; default gross)")
    p.add_argument("--fx", type=float, default=5.0, help="Câmbio USD→BRL (default 5,0)")
    p.add_argument("--cenarios", help="'Base:5,Target:10,Homerun:30' (default)")
    # Output
    p.add_argument("--output", help="Caminho HTML; se omitido, só imprime no terminal/chat")
    args = p.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION, source="github")
        except Exception:
            pass

    r = compute(args)
    print_result(r)

    if args.output:
        out = Path(args.output)
        render_html(r, out)
        print(f"  HTML gerado: {out}")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    print("\n— Powered by Zivo · Free skills for HR & People leaders · https://zivo.ai?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=total-comp-calculator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
