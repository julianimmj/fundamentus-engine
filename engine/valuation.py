"""
valuation.py — Camada 4b: Valuation (DCF + Múltiplos + Sensibilidade)
Calcula Target Price via DCF com WACC detalhado + múltiplos comparáveis.
"""
import logging
import numpy as np
from engine.config import (
    ERP_DEFAULT, TERMINAL_GROWTH_BR, TERMINAL_GROWTH_US,
    TAX_RATE_BR, PROJECTION_YEARS, TICKER_SECTOR
)

logger = logging.getLogger(__name__)


def compute_wacc(company, macro_global, macro_brazil):
    """
    Compute WACC (Weighted Average Cost of Capital).
    
    WACC = E/(E+D) × Ke + D/(E+D) × Kd × (1-t)
    
    Ke = Rf + β × (ERP + CRP)
    """
    # Risk-free rate: US 10Y Treasury
    rf = macro_global.get("indicators", {}).get("us_10y", {})
    rf_rate = rf.get("current", 4.5) / 100 if isinstance(rf, dict) else 0.045

    # Beta
    beta = company.get("beta", 1.0) or 1.0
    beta = max(0.3, min(3.0, beta))  # Clamp to reasonable range

    # Country Risk Premium (CDS 5Y spread proxy)
    # Estimate from USD/BRL level if CDS not available
    usd = macro_brazil.get("indicators", {}).get("usdbrl", {})
    usd_val = usd.get("current", 5.0) if isinstance(usd, dict) else 5.0
    # CRP heuristic: higher USD/BRL = higher country risk
    crp = max(0.015, min(0.06, (usd_val - 3.5) * 0.015))

    # ERP (Equity Risk Premium)
    erp = ERP_DEFAULT

    # Cost of Equity
    sector = TICKER_SECTOR.get(company.get("ticker", ""), "")
    is_bdr = sector.startswith("bdr_")
    
    if is_bdr:
        ke = rf_rate + beta * erp  # No CRP for US companies
    else:
        ke = rf_rate + beta * (erp + crp)

    # Cost of Debt
    interest = company.get("interest_expense")
    total_debt = company.get("total_debt")
    if interest and total_debt and total_debt > 0:
        kd = abs(interest) / total_debt
        kd = max(0.04, min(0.25, kd))
    else:
        # Default: Selic + spread
        selic = macro_brazil.get("indicators", {}).get("selic_meta", 13.75) / 100
        kd = selic + 0.025 if not is_bdr else rf_rate + 0.02

    # Capital structure
    equity_val = company.get("market_cap") or company.get("equity")
    debt_val = total_debt or 0

    if equity_val and equity_val > 0:
        total_capital = equity_val + debt_val
        w_equity = equity_val / total_capital
        w_debt = debt_val / total_capital
    else:
        w_equity, w_debt = 0.7, 0.3

    tax = TAX_RATE_BR if not is_bdr else 0.21

    wacc = w_equity * ke + w_debt * kd * (1 - tax)
    wacc = max(0.06, min(0.25, wacc))  # Clamp

    return {
        "wacc": round(wacc, 4),
        "ke": round(ke, 4),
        "kd": round(kd, 4),
        "rf": round(rf_rate, 4),
        "beta": round(beta, 2),
        "erp": round(erp, 4),
        "crp": round(crp, 4),
        "w_equity": round(w_equity, 4),
        "w_debt": round(w_debt, 4),
    }


def compute_dcf(company, wacc_data):
    """
    Discounted Cash Flow valuation.
    
    Enterprise Value = Σ FCFᵢ/(1+WACC)^i + Terminal Value/(1+WACC)^n
    Equity Value = EV - Net Debt
    Target Price = Equity Value / Shares Outstanding
    """
    projections = company.get("projections", {})
    fcff_list = projections.get("fcff", [])

    if not fcff_list or len(fcff_list) < PROJECTION_YEARS:
        return None

    wacc = wacc_data["wacc"]
    sector = TICKER_SECTOR.get(company.get("ticker", ""), "")
    is_bdr = sector.startswith("bdr_")
    terminal_g = TERMINAL_GROWTH_US if is_bdr else TERMINAL_GROWTH_BR

    # Discount FCFs
    pv_fcfs = sum(
        fcf / (1 + wacc) ** (i + 1)
        for i, fcf in enumerate(fcff_list)
    )

    # Terminal Value (Gordon Growth Model)
    last_fcf = fcff_list[-1]
    if wacc <= terminal_g:
        terminal_g = wacc - 0.01

    terminal_value = last_fcf * (1 + terminal_g) / (wacc - terminal_g)
    pv_terminal = terminal_value / (1 + wacc) ** PROJECTION_YEARS

    # Enterprise Value
    ev = pv_fcfs + pv_terminal

    # Equity Value
    net_debt = company.get("net_debt", 0) or 0
    equity_value = ev - net_debt

    # Target Price
    shares = company.get("shares_outstanding")
    if not shares or shares <= 0:
        return None

    target_price = equity_value / shares
    current_price = company.get("current_price", 0)
    upside = (target_price / current_price - 1) if current_price and current_price > 0 else None

    return {
        "pv_fcfs": round(pv_fcfs),
        "terminal_value": round(terminal_value),
        "pv_terminal": round(pv_terminal),
        "enterprise_value": round(ev),
        "equity_value": round(equity_value),
        "target_price_dcf": round(target_price, 2),
        "upside_dcf": round(upside, 4) if upside is not None else None,
    }


def compute_multiples_valuation(company, sector_metrics):
    """
    Valuation via comparable multiples.
    Target price implied by sector median multiples.
    """
    targets = []

    # EV/EBITDA
    ev_ebitda_median = sector_metrics.get("ev_ebitda_median")
    ebitda = company.get("ebitda_latest")
    net_debt = company.get("net_debt", 0) or 0
    shares = company.get("shares_outstanding")

    if ev_ebitda_median and ebitda and ebitda > 0 and shares and shares > 0:
        implied_ev = ebitda * ev_ebitda_median
        implied_equity = implied_ev - net_debt
        if implied_equity > 0:
            targets.append(("EV/EBITDA", implied_equity / shares))

    # P/E
    pe_median = sector_metrics.get("pe_median")
    eps = company.get("net_income_latest")
    if pe_median and eps and eps > 0 and shares and shares > 0:
        eps_per_share = eps / shares
        targets.append(("P/E", eps_per_share * pe_median))

    # P/BV
    pb_median = sector_metrics.get("pb_median")
    equity = company.get("equity")
    if not pb_median:
        pb_median = company.get("pb_ratio")
    if pb_median and equity and equity > 0 and shares and shares > 0:
        bvps = equity / shares
        targets.append(("P/BV", bvps * pb_median))

    if not targets:
        return None

    avg_target = np.mean([t[1] for t in targets])
    current = company.get("current_price", 0) or 0
    upside = (avg_target / current - 1) if current > 0 else None

    return {
        "multiples_details": {name: round(val, 2) for name, val in targets},
        "target_price_multiples": round(avg_target, 2),
        "upside_multiples": round(upside, 4) if upside is not None else None,
    }


def compute_sensitivity_table(company, wacc_data):
    """
    Sensitivity analysis: Target Price for WACC ±1% and Terminal Growth ±0.5%.
    Returns 5x5 matrix.
    """
    wacc_base = wacc_data["wacc"]
    sector = TICKER_SECTOR.get(company.get("ticker", ""), "")
    is_bdr = sector.startswith("bdr_")
    tg_base = TERMINAL_GROWTH_US if is_bdr else TERMINAL_GROWTH_BR

    projections = company.get("projections", {})
    fcff_list = projections.get("fcff", [])
    net_debt = company.get("net_debt", 0) or 0
    shares = company.get("shares_outstanding")

    if not fcff_list or not shares or shares <= 0:
        return None

    wacc_range = [wacc_base + d for d in [-0.02, -0.01, 0, 0.01, 0.02]]
    tg_range = [tg_base + d for d in [-0.01, -0.005, 0, 0.005, 0.01]]

    table = []
    for w in wacc_range:
        row = []
        for g in tg_range:
            if w <= g:
                row.append(None)
                continue
            pv = sum(f / (1 + w) ** (i + 1) for i, f in enumerate(fcff_list))
            tv = fcff_list[-1] * (1 + g) / (w - g)
            pv_tv = tv / (1 + w) ** len(fcff_list)
            eq_val = pv + pv_tv - net_debt
            tp = eq_val / shares if eq_val > 0 else 0
            row.append(round(tp, 2))
        table.append(row)

    return {
        "wacc_range": [round(w, 4) for w in wacc_range],
        "tg_range": [round(g, 4) for g in tg_range],
        "target_prices": table,
    }


def compute_final_target(company, dcf_result, multiples_result):
    """
    Blended target price: 50% DCF + 30% Multiples + 20% DDM (if applicable).
    """
    targets = []
    weights = []

    if dcf_result and dcf_result.get("target_price_dcf"):
        tp = dcf_result["target_price_dcf"]
        if tp > 0:
            targets.append(tp)
            weights.append(0.50)

    if multiples_result and multiples_result.get("target_price_multiples"):
        tp = multiples_result["target_price_multiples"]
        if tp > 0:
            targets.append(tp)
            weights.append(0.30)

    # DDM (Dividend Discount Model) - simplified
    dy = company.get("dividend_yield")
    price = company.get("current_price", 0)
    if dy and dy > 0.02 and price and price > 0:
        # Gordon model: P = D / (Ke - g)
        dividend = price * dy
        ke = 0.12  # Simplified
        g = 0.04
        if ke > g:
            ddm_target = dividend * 1.04 / (ke - g)
            if ddm_target > 0:
                targets.append(ddm_target)
                weights.append(0.20)

    if not targets:
        return {"target_price": None, "upside": None, "method": "N/A"}

    # Normalize weights
    total_w = sum(weights)
    final_tp = sum(t * w / total_w for t, w in zip(targets, weights))

    current = company.get("current_price", 0) or 0
    upside = (final_tp / current - 1) if current > 0 else None

    # Sanity check: clamp extreme values (max ±100%)
    if upside and abs(upside) > 1.0:
        final_tp = current * (1 + np.sign(upside) * 1.0)
        upside = np.sign(upside) * 1.0

    return {
        "target_price": round(final_tp, 2),
        "upside": round(upside, 4) if upside is not None else None,
        "method": f"DCF({int(weights[0]/total_w*100)}%) + Mult({int(weights[1]/total_w*100 if len(weights)>1 else 0)}%)",
    }


def run_valuation(company, macro_global, macro_brazil, sector_metrics=None):
    """
    Full valuation pipeline for a single company.
    Returns dict with all valuation results.
    """
    if not company.get("has_financials") or company.get("error"):
        return {"error": "No financial data available"}

    # WACC
    wacc_data = compute_wacc(company, macro_global, macro_brazil)

    # DCF
    dcf_result = compute_dcf(company, wacc_data)

    # Multiples
    sect_met = sector_metrics or {}
    multiples_result = compute_multiples_valuation(company, sect_met)

    # Final Target
    final = compute_final_target(company, dcf_result, multiples_result)

    # Sensitivity
    sensitivity = compute_sensitivity_table(company, wacc_data)

    return {
        "wacc": wacc_data,
        "dcf": dcf_result,
        "multiples": multiples_result,
        "sensitivity": sensitivity,
        "target_price": final.get("target_price"),
        "upside": final.get("upside"),
        "method": final.get("method"),
    }
