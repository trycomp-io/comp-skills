#!/usr/bin/env python3
"""
total_comp.py — Calculadora de Total Compensation (modelo Comp).

Monta o pacote completo de remuneração: salário base + benefícios + variável
(bonus/ICP) + equity (SOP/ILP com cenários de exit). Produz 2 headline numbers
(near-term e long-term) + breakdown detalhado + visão visual HTML.

Estrutura baseada no modelo de Total Comp da Comp:
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
      <table>
        <thead><tr><th>Cenário</th><th>Múlt.</th><th>Total R$</th><th>Anual R$</th><th>Total Cash + Stocks/ano</th></tr></thead>
        <tbody>{cenario_rows}</tbody>
      </table>
      <p class="note">Valor {'líquido de strike' if sop['net_of_strike'] else 'gross (não deduz strike)'}. Anual = total ÷ {sop['vesting_years']} anos de vesting. ILP no headline usa o cenário <strong>{_esc(sop['target_name'] or 'Target')}</strong>.</p>
    </div>""".replace(",", ".") if sop else ""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Total Compensation — Comp</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
  body{{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b}}
  .card{{background:white;border-radius:12px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin-bottom:1.5rem}}
  h2{{font-size:1.15rem;font-weight:700;color:#0f172a;margin-bottom:1rem}}
  table{{width:100%;border-collapse:collapse;font-size:.9rem}}
  th{{background:#1e293b;color:white;padding:.6rem;text-align:left;font-size:.7rem;text-transform:uppercase}}
  td{{padding:.6rem;border-bottom:1px solid #e2e8f0}}
  .headline{{background:#FFE600;border-radius:12px;padding:1.5rem 2rem;display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem}}
  .headline-2{{background:#fef9c3}}
  .headline-label{{font-size:.95rem;font-weight:600;color:#0f172a}}
  .headline-sub{{font-size:.8rem;color:#475569;font-style:italic}}
  .headline-val{{font-size:2rem;font-weight:900;color:#0f172a}}
  .sop-meta{{display:flex;flex-wrap:wrap;gap:.5rem 1.5rem;font-size:.85rem;color:#475569;margin-bottom:1rem}}
  .note{{font-size:.8rem;color:#64748b;margin-top:.75rem}}
  .bar{{display:flex;height:40px;border-radius:8px;overflow:hidden;margin:1rem 0}}
  .seg-base{{background:#1e293b}}.seg-benef{{background:#0ea5e9}}.seg-bonus{{background:#f59e0b}}.seg-ilp{{background:#10b981}}
  .legend{{display:flex;flex-wrap:wrap;gap:1rem;font-size:.8rem}}
  .legend span{{display:flex;align-items:center;gap:.4rem}}
  .dot{{width:12px;height:12px;border-radius:3px;display:inline-block}}
</style></head>
<body class="p-6 sm:p-10"><div class="max-w-4xl mx-auto">

<header class="mb-8 flex justify-between items-start">
<div>
<div class="text-xs uppercase tracking-wider text-rose-600 font-bold mb-1">Total Compensation</div>
<h1 class="text-3xl font-extrabold text-slate-900">Pacote de remuneração</h1>
<p class="text-sm text-slate-500 mt-2">Gerado em {datetime.now().strftime('%d/%m/%Y')}</p>
</div>
<img src="https://i.ibb.co/KxDQ7BKQ/SIMBOLO-COMP-RGB-VERMELHO-G.png" alt="Comp" class="h-10 w-10">
</header>

<div class="headline">
  <div><div class="headline-label">TOTAL COMP (long-term, anual)</div><div class="headline-sub">{_esc(h['long_label'])}</div></div>
  <div class="headline-val">{fmt_brl(h['long_term'])}</div>
</div>
<div class="headline headline-2">
  <div><div class="headline-label">TOTAL COMP (near-term, anual)</div><div class="headline-sub">{_esc(h['near_label'])}</div></div>
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
<table>
<tbody>
<tr><td>Salário base mensal</td><td>{fmt_brl(c['base_mensal'])}</td></tr>
<tr><td>Salário base anual</td><td>{fmt_brl(c['base_anual'])}</td></tr>
<tr><td>Bônus anual</td><td>{fmt_brl(c['bonus_anual'])}</td></tr>
<tr><td><strong>Total Cash anual</strong></td><td><strong>{fmt_brl(c['total_cash_anual'])}</strong></td></tr>
<tr><td>Base mensal + benefícios</td><td>{fmt_brl(c['base_mensal_com_beneficios'])}</td></tr>
</tbody>
</table>
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

<footer style="margin-top:48px;padding:24px 0;border-top:1px solid #e5e7eb;text-align:center;font-family:'Inter',sans-serif;font-size:13px;color:#6b7280;">
Powered by <a href="https://comp.vc?utm_source=skill-output&amp;utm_medium=html-footer&amp;utm_campaign=eam&amp;utm_content=total-comp-calculator" style="color:#ff4456;text-decoration:none;font-weight:600;">Comp</a>
— Free skills for HR &amp; People leaders.
</footer>
</div></body></html>
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")


def _esc(s):
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ========== CLI ==========


def main() -> int:
    p = argparse.ArgumentParser(description="Calculadora de Total Compensation (modelo Comp).")
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

    print("\n— Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=cli-footer&utm_campaign=eam&utm_content=total-comp-calculator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
