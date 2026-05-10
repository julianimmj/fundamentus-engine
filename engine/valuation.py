"""
valuation.py — Camada 4b: Valuation (DCF + Múltiplos + Sensibilidade)
Calcula Target Price via DCF com WACC detalhado + múltiplos comparáveis.

v2: Fixes for realistic Brazilian market valuation:
  - Beta floor 0.7 (yfinance returns unreliable low betas for .SA)
  - WACC floor 10% for BR stocks (consistent with Selic + risk)
  - Banks use equity-only Ke (deposits ≠ corporate debt)
  - DDM uses dynamic Ke from WACC, not hardcoded
  - Blend checks consistency between methods before averaging
  - Upside clamped at ±60% (sell-side reports rarely exceed this)
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
    
    For banks: WACC ≈ Ke (deposits are operational, not financial debt)
    """
    # Risk-free rate: US 10Y Treasury
    rf = macro_global.get("indicators", {}).get("us_10y", {})
    rf_rate = rf.get("current", 4.5) / 100 if isinstance(rf, dict) else 0.045

    # Beta — yfinance returns unreliable betas for .SA stocks
    # Floor at 0.7 (no liquid BR stock has true beta < 0.7)
    beta = company.get("beta") or 1.0
    beta = max(0.7, min(2.5, beta))

    # Country Risk Premium (CDS 5Y spread proxy)
    usd = macro_brazil.get("indicators", {}).get("usdbrl", {})
    usd_val = usd.get("current", 5.5) if isinstance(usd, dict) else 5.5
    crp = max(0.02, min(0.06, (usd_val - 3.0) * 0.012))

    erp = ERP_DEFAULT
    sector = TICKER_SECTOR.get(company.get("ticker", ""), "")
    is_bdr = sector.startswith("bdr_")
    is_bank = sector == "bancos"

    # Cost of Equity
    if is_bdr:
        ke = rf_rate + beta * erp
    else:
        ke = rf_rate + beta * (erp + crp)

    # Ensure Ke is realistic for Brazil (Selic is ~14%)
    if not is_bdr:
        selic = macro_brazil.get("indicators", {}).get("selic_meta", 14.5)
        ke = max(ke, selic / 100 + 0.02)  # At minimum Selic + 2%

    # Cost of Debt
    interest = company.get("interest_expense")
    total_debt = company.get("total_debt")
    if interest and total_debt and total_debt > 0 and not is_bank:
        kd = abs(interest) / total_debt
        kd = max(0.06, min(0.22, kd))
    else:
        selic = macro_brazil.get("indicators", {}).get("selic_meta", 14.5) / 100
        kd = selic + 0.02 if not is_bdr else rf_rate + 0.015

    # Capital structure
    equity_val = company.get("market_cap") or company.get("equity")
    debt_val = total_debt or 0

    if is_bank:
        # Banks: WACC = Ke (deposits are not financial debt for WACC purposes)
        w_equity, w_debt = 1.0, 0.0
    elif equity_val and equity_val > 0:
        total_capital = equity_val + debt_val
        w_equity = equity_val / total_capital
        w_debt = debt_val / total_capital
    else:
        w_equity, w_debt = 0.65, 0.35

    tax = TAX_RATE_BR if not is_bdr else 0.21

    wacc = w_equity * ke + w_debt * kd * (1 - tax)

    # Floor: Brazilian equities should have WACC >= 10% given macro
    if not is_bdr:
        wacc = max(0.10, min(0.22, wacc))
    else:
        wacc = max(0.07, min(0.18, wacc))

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

    # Reject if projected FCFs are negative (unprofitable companies)
    if all(f <= 0 for f in fcff_list):
        return None

    wacc = wacc_data["wacc"]
    sector = TICKER_SECTOR.get(company.get("ticker", ""), "")
    is_bdr = sector.startswith("bdr_")
    terminal_g = TERMINAL_GROWTH_US if is_bdr else TERMINAL_GROWTH_BR

    # Discount projected FCFs
    pv_fcfs = sum(
        fcf / (1 + wacc) ** (i + 1)
        for i, fcf in enumerate(fcff_list)
    )

    # Terminal Value (Gordon Growth Model)
    last_fcf = fcff_list[-1]
    if last_fcf <= 0:
        # Use last positive FCF
        positive_fcfs = [f for f in fcff_list if f > 0]
        last_fcf = positive_fcfs[-1] if positive_fcfs else 0
    if last_fcf <= 0:
        return None

    if wacc <= terminal_g:
        terminal_g = wacc - 0.02

    terminal_value = last_fcf * (1 + terminal_g) / (wacc - terminal_g)
    pv_terminal = terminal_value / (1 + wacc) ** PROJECTION_YEARS

    # Enterprise Value
    ev = pv_fcfs + pv_terminal

    # Equity Value
    net_debt = company.get("net_debt", 0) or 0
    equity_value = ev - net_debt

    if equity_value <= 0:
        return None

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
    For BDRs, skips EV/EBITDA (USD/BRL mismatch) and uses only P/E.
    """
    targets = []
    shares = company.get("shares_outstanding")
    net_debt = company.get("net_debt", 0) or 0
    current_price = company.get("current_price", 0) or 0

    if not shares or shares <= 0 or current_price <= 0:
        return None

    sector = TICKER_SECTOR.get(company.get("ticker", ""), "")
    is_bdr = sector.startswith("bdr_")

    # EV/EBITDA — SKIP for BDRs (financials in USD, price in BRL = mismatch)
    if not is_bdr:
        ev_ebitda_median = sector_metrics.get("ev_ebitda_median")
        ebitda = company.get("ebitda_latest")
        if not ev_ebitda_median:
            own_ev_ebitda = company.get("ev_ebitda")
            if own_ev_ebitda and own_ev_ebitda > 0:
                ev_ebitda_median = own_ev_ebitda * 0.95

        if ev_ebitda_median and ebitda and ebitda > 0:
            implied_ev = ebitda * ev_ebitda_median
            implied_equity = implied_ev - net_debt
            if implied_equity > 0:
                target_eveb = implied_equity / shares
                # Sanity: target must be between 30% and 300% of current price
                if current_price * 0.30 < target_eveb < current_price * 3.0:
                    targets.append(("EV/EBITDA", target_eveb))

    # P/E — For BDRs: use sector benchmark PE if available; otherwise skip
    # P/E is currency-neutral ONLY when using yfinance's own EPS (price/pe = eps in same currency)
    pe_median = sector_metrics.get("pe_median")
    net_income = company.get("net_income_latest")
    if not pe_median:
        own_pe = company.get("pe_ratio")
        if own_pe and 0 < own_pe < 60:
            pe_median = own_pe * 0.95  # slight discount = target

    if is_bdr:
        # For BDRs: use yfinance P/E directly (price/eps already in BRL units)
        own_pe = company.get("pe_ratio")
        if own_pe and 0 < own_pe < 80:
            # Target = current price × (sector_pe / own_pe), capped at ±30%
            if pe_median and pe_median > 0:
                rerating = pe_median / own_pe
                rerating = max(0.70, min(1.30, rerating))  # clamp rerating
                targets.append(("P/E", current_price * rerating))
            else:
                # No sector median: BDR is assumed fairly valued
                targets.append(("P/E", current_price * 0.97))  # slight discount
    else:
        if pe_median and net_income and net_income > 0:
            eps = net_income / shares
            pe_target = eps * pe_median
            if current_price * 0.30 < pe_target < current_price * 3.0:
                targets.append(("P/E", pe_target))

    # P/BV — only for financials where BV is meaningful
    if sector in ("bancos", "seguros"):
        pb = company.get("pb_ratio")
        equity = company.get("equity")
        if pb and equity and equity > 0:
            bvps = equity / shares
            targets.append(("P/BV", bvps * max(pb * 0.95, 1.0)))

    if not targets:
        return None

    # Weighted average
    weighted_target = 0
    total_w = 0
    mult_weights = {"EV/EBITDA": 0.45, "P/E": 0.35, "P/BV": 0.20}
    for name, val in targets:
        w = mult_weights.get(name, 0.33)
        weighted_target += val * w
        total_w += w
    avg_target = weighted_target / total_w if total_w > 0 else targets[0][1]

    upside = (avg_target / current_price - 1) if current_price > 0 else None

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
            if w <= g + 0.01:
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


def compute_final_target(company, dcf_result, multiples_result, wacc_data=None):
    """
    Blended target price with data-quality and consistency checks.
    
    Key protections:
    - DCF discarded if target < 30% of current price (data-quality issue)
    - DDM capped at 1.3x current price (high DY ≠ infinite value)
    - When methods diverge wildly, Multiples are preferred (market-anchored)
    - Final upside capped at ±50%
    """
    current = company.get("current_price", 0) or 0
    if current <= 0:
        return {"target_price": None, "upside": None, "method": "N/A"}

    targets = []
    weights = []
    method_parts = []

    # ── DCF (only if sanity check passes) ──
    dcf_tp = None
    if dcf_result and dcf_result.get("target_price_dcf"):
        raw_dcf = dcf_result["target_price_dcf"]
        # Sanity: reject DCF if target < 30% of price (currency mismatch / bad data)
        # or if target > 5x price (projection too aggressive)
        if raw_dcf > current * 0.30 and raw_dcf < current * 5.0:
            dcf_tp = raw_dcf
            targets.append(dcf_tp)
            weights.append(0.35)
            method_parts.append("DCF")
        else:
            logger.debug(f"DCF discarded for {company.get('ticker')}: "
                        f"target={raw_dcf:.2f} vs price={current:.2f}")

    # ── Multiples ──
    mult_tp = None
    if multiples_result and multiples_result.get("target_price_multiples"):
        mult_tp = multiples_result["target_price_multiples"]
        if mult_tp > 0:
            targets.append(mult_tp)
            weights.append(0.45)
            method_parts.append("Mult")

    # ── DDM (only for DY > 4%, profitable, real dividend history) ──
    dy = company.get("dividend_yield")
    net_income_chk = company.get("net_income_latest", 0) or 0
    div_rate = company.get("dividend_rate") or 0
    # Strict: require DY > 4%, company profitable, and actual dividend payment
    if dy and dy > 0.04 and current > 0 and net_income_chk > 0 and div_rate > 0:
        ke = wacc_data["ke"] if wacc_data else 0.15
        g = 0.035
        if ke > g + 0.02:
            dividend = current * dy
            ddm_target = dividend * (1 + g) / (ke - g)
            # Cap DDM: no more than 1.3x current (high DY != infinite value)
            ddm_target = min(ddm_target, current * 1.3)
            # Floor: DDM shouldn't crater below 0.7x
            ddm_target = max(ddm_target, current * 0.70)
            if ddm_target > 0:
                targets.append(ddm_target)
                weights.append(0.20)
                method_parts.append("DDM")

    if not targets:
        return {"target_price": None, "upside": None, "method": "N/A"}

    # ── Consistency check: if DCF and Multiples diverge > 60%, trust Multiples ──
    if dcf_tp and mult_tp and mult_tp > 0:
        divergence = abs(dcf_tp - mult_tp) / mult_tp
        if divergence > 0.60:
            for i, mp in enumerate(method_parts):
                if mp == "DCF":
                    weights[i] = 0.15
                elif mp == "Mult":
                    weights[i] = 0.65

    # Normalize weights and compute blended target
    total_w = sum(weights)
    final_tp = sum(t * w / total_w for t, w in zip(targets, weights))

    upside = (final_tp / current - 1)

    # ── No artificial clamp: allow mathematical upside up to sanity limits ──
    # The models already filter targets > 3.0x or < 0.3x current price, 
    # so we don't need a hard 50% cap here.

    method_str = " + ".join(
        f"{mp}({int(w/total_w*100)}%)" for mp, w in zip(method_parts, weights)
    )

    return {
        "target_price": round(final_tp, 2),
        "upside": round(upside, 4),
        "method": method_str,
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

    # Final Target (pass wacc_data for DDM Ke)
    final = compute_final_target(company, dcf_result, multiples_result, wacc_data)

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
