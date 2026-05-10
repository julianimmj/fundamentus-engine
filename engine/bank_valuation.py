"""
bank_valuation.py — Valuation especializado para Bancos
Modelos: DDM 2-estágios, Residual Income, P/BV Justificado, Equity DCF.
Não usa WACC/Firm — usa Ke (Cost of Equity) diretamente.
"""
import logging
import numpy as np
import yfinance as yf
from engine.config import (
    BANK_PEERS, ERP_DEFAULT, TERMINAL_GROWTH_BR
)

logger = logging.getLogger(__name__)


def compute_bank_ke(bank_data, macro_global, macro_brazil):
    """
    Compute Cost of Equity (Ke) for a bank.
    Banks use Ke directly (no WACC since deposits aren't financial debt).
    """
    # Risk-free rate
    rf = macro_global.get("indicators", {}).get("us_10y_yield", 4.5) / 100
    if rf > 0.12:
        rf = 0.045

    # Country Risk Premium
    crp = macro_brazil.get("indicators", {}).get("embi", 230) / 10000
    if crp > 0.10:
        crp = 0.023

    # Beta for banks (typically 0.8-1.2)
    beta = bank_data.get("beta") or 1.0
    beta = max(0.7, min(1.4, beta))

    # ERP
    erp = ERP_DEFAULT

    # Ke = Rf + Beta * ERP + CRP
    ke = rf + beta * erp + crp

    # Floor: Brazilian banks Ke should be at least 13%
    ke = max(ke, 0.13)

    return {
        "ke": round(ke, 4),
        "rf": round(rf, 4),
        "beta": round(beta, 2),
        "erp": erp,
        "crp": round(crp, 4),
    }


def compute_ddm(bank_data, ke_data, terminal_growth=None):
    """
    DDM 2-Stage: Dividend Discount Model.
    
    Stage 1: Project dividends for 5 years using bank projections
    Stage 2: Terminal value using Gordon Growth Model
    
    Returns target price per share.
    """
    shares = bank_data.get("shares_outstanding")
    if not shares or shares <= 0:
        return None

    ke = ke_data["ke"]
    tg = terminal_growth or TERMINAL_GROWTH_BR

    if ke <= tg + 0.01:
        return None

    projections = bank_data.get("projections", {})
    dividends = projections.get("dividends", [])

    if not dividends or len(dividends) < 3:
        # Fallback: project from current dividend
        price = bank_data.get("current_price", 0) or 0
        dy = bank_data.get("dividend_yield")
        if not dy or dy <= 0 or price <= 0:
            return None
        dividend = price * dy
        # Simple growth fade
        g_initial = 0.08
        dividends = [
            dividend * (1 + g_initial - 0.01 * i)
            for i in range(5)
        ]

    # Stage 1: PV of explicit dividends
    pv_stage1 = sum(
        d / (1 + ke) ** (i + 1) for i, d in enumerate(dividends)
    )

    # Stage 2: Terminal value (Gordon Growth)
    terminal_div = dividends[-1] * (1 + tg)
    tv = terminal_div / (ke - tg)
    pv_tv = tv / (1 + ke) ** len(dividends)

    equity_value = pv_stage1 + pv_tv

    if equity_value <= 0:
        return None

    target_price = equity_value / shares

    return {
        "model": "DDM",
        "target_price": round(target_price, 2),
        "equity_value": round(equity_value),
        "pv_stage1": round(pv_stage1),
        "pv_terminal": round(pv_tv),
        "ke": ke,
        "terminal_growth": tg,
    }


def compute_residual_income(bank_data, ke_data, terminal_growth=None):
    """
    Residual Income Model (RIM).
    
    Value = Book Value + PV of future residual income
    Residual Income = Net Income - Ke × Book Value
    
    Best for banks because book value is a meaningful anchor.
    """
    shares = bank_data.get("shares_outstanding")
    equity = bank_data.get("equity")
    if not shares or not equity or shares <= 0 or equity <= 0:
        return None

    ke = ke_data["ke"]
    tg = terminal_growth or TERMINAL_GROWTH_BR

    if ke <= tg + 0.01:
        return None

    projections = bank_data.get("projections", {})
    proj_ni = projections.get("net_income", [])
    proj_eq = projections.get("equity", [])

    if not proj_ni or len(proj_ni) < 3:
        return None

    bv_per_share = equity / shares

    # PV of residual income
    pv_ri = 0
    prev_equity = equity
    for i, (ni, eq) in enumerate(zip(proj_ni, proj_eq)):
        ri = ni - ke * prev_equity
        pv_ri += ri / (1 + ke) ** (i + 1)
        prev_equity = eq

    # Terminal residual income
    if proj_ni and proj_eq:
        terminal_ri = proj_ni[-1] - ke * proj_eq[-1]
        if terminal_ri > 0:
            tv_ri = terminal_ri * (1 + tg) / (ke - tg)
        else:
            tv_ri = 0
        pv_tv_ri = tv_ri / (1 + ke) ** len(proj_ni)
    else:
        pv_tv_ri = 0

    total_equity_value = equity + pv_ri + pv_tv_ri

    if total_equity_value <= 0:
        return None

    target_price = total_equity_value / shares

    return {
        "model": "RIM",
        "target_price": round(target_price, 2),
        "equity_value": round(total_equity_value),
        "book_value_ps": round(bv_per_share, 2),
        "pv_residual_income": round(pv_ri),
        "pv_terminal_ri": round(pv_tv_ri),
    }


def compute_justified_pbv(bank_data, ke_data, terminal_growth=None):
    """
    Justified P/BV Model.
    
    P/BV_justified = (ROE - g) / (Ke - g)
    
    If ROE > Ke: bank deserves P/BV > 1 (creates value)
    If ROE < Ke: bank deserves P/BV < 1 (destroys value)
    """
    equity = bank_data.get("equity")
    shares = bank_data.get("shares_outstanding")
    roe = bank_data.get("roe")

    if not equity or not shares or not roe or shares <= 0:
        return None

    ke = ke_data["ke"]
    g = terminal_growth or TERMINAL_GROWTH_BR

    if ke <= g + 0.01:
        return None

    # Sustainable ROE (average of current and target)
    sustainable_roe = max(0.08, min(0.30, roe))

    justified_pbv = (sustainable_roe - g) / (ke - g)
    justified_pbv = max(0.3, min(4.0, justified_pbv))

    bv_per_share = equity / shares
    target_price = bv_per_share * justified_pbv

    current_pbv = bank_data.get("pb_ratio")

    return {
        "model": "P/BV Justified",
        "target_price": round(target_price, 2),
        "justified_pbv": round(justified_pbv, 2),
        "current_pbv": round(current_pbv, 2) if current_pbv else None,
        "bv_per_share": round(bv_per_share, 2),
        "sustainable_roe": round(sustainable_roe, 4),
    }


def compute_equity_dcf(bank_data, ke_data, terminal_growth=None):
    """
    Equity DCF (Direct FCFE Discounting).
    
    FCFE = Net Income - ΔEquity (capital needed to maintain growth)
    """
    shares = bank_data.get("shares_outstanding")
    if not shares or shares <= 0:
        return None

    ke = ke_data["ke"]
    tg = terminal_growth or TERMINAL_GROWTH_BR

    if ke <= tg + 0.01:
        return None

    projections = bank_data.get("projections", {})
    fcfe = projections.get("fcfe", [])

    if not fcfe or len(fcfe) < 3:
        return None

    # Filter out negative FCFE (banks may need capital to grow)
    valid_fcfe = [max(f, 0) for f in fcfe]

    if sum(valid_fcfe) <= 0:
        return None

    # PV of FCFE
    pv = sum(f / (1 + ke) ** (i + 1) for i, f in enumerate(valid_fcfe))

    # Terminal value
    terminal_fcfe = valid_fcfe[-1] * (1 + tg)
    tv = terminal_fcfe / (ke - tg)
    pv_tv = tv / (1 + ke) ** len(valid_fcfe)

    equity_value = pv + pv_tv

    if equity_value <= 0:
        return None

    target_price = equity_value / shares

    return {
        "model": "Equity DCF",
        "target_price": round(target_price, 2),
        "equity_value": round(equity_value),
        "pv_fcfe": round(pv),
        "pv_terminal": round(pv_tv),
    }


def compute_bank_multiples(bank_data, peer_data=None):
    """
    Relative valuation using bank-specific multiples.
    Compares P/BV, P/E, and implied ROE vs peers.
    """
    shares = bank_data.get("shares_outstanding")
    price = bank_data.get("current_price")
    if not shares or not price or shares <= 0 or price <= 0:
        return None

    # Fetch peer data for comparison
    peer_multiples = _fetch_peer_multiples()

    if not peer_multiples:
        return None

    targets = []
    weights = []

    # P/BV relative
    pbv = bank_data.get("pb_ratio")
    median_pbv = np.median([p["pbv"] for p in peer_multiples if p.get("pbv")])
    equity = bank_data.get("equity")
    if pbv and median_pbv and equity and equity > 0:
        bvps = equity / shares
        target_pbv = bvps * median_pbv
        targets.append(target_pbv)
        weights.append(0.50)

    # P/E relative
    pe = bank_data.get("pe_ratio")
    median_pe = np.median([p["pe"] for p in peer_multiples if p.get("pe")])
    net_income = bank_data.get("net_income_latest")
    if pe and median_pe and net_income and net_income > 0:
        eps = net_income / shares
        target_pe = eps * median_pe
        if target_pe > 0:
            targets.append(target_pe)
            weights.append(0.50)

    if not targets:
        return None

    total_w = sum(weights)
    blended = sum(t * w / total_w for t, w in zip(targets, weights))

    return {
        "model": "Bank Multiples",
        "target_price": round(blended, 2),
        "median_peer_pbv": round(median_pbv, 2) if median_pbv else None,
        "median_peer_pe": round(median_pe, 1) if median_pe else None,
    }


def _fetch_peer_multiples():
    """Fetch P/BV and P/E for bank peers (cached)."""
    cache = get_cache()
    cached = cache.get("bank_peer_multiples", category="fundamentals")
    if cached:
        return cached

    peers = []
    for ticker in BANK_PEERS:
        try:
            info = yf.Ticker(ticker).info or {}
            pbv = info.get("priceToBook")
            pe = info.get("trailingPE") or info.get("forwardPE")
            if pbv or pe:
                peers.append({
                    "ticker": ticker,
                    "pbv": pbv,
                    "pe": pe,
                })
        except Exception:
            pass

    if peers:
        cache.set("bank_peer_multiples", peers, category="fundamentals")

    return peers


from engine.cache import get_cache


def run_bank_valuation(bank_data, macro_global, macro_brazil):
    """
    Full bank valuation pipeline.
    
    Blends 4 models:
    - DDM 2-Stage (35%)
    - Residual Income (25%)
    - P/BV Justified (25%)
    - Equity DCF (15%)
    
    Returns same format as run_valuation() for pipeline compatibility.
    """
    if not bank_data.get("has_financials") or bank_data.get("error"):
        return {"error": "No financial data available"}

    current = bank_data.get("current_price", 0) or 0
    if current <= 0:
        return {"error": "No price available"}

    # Cost of Equity
    ke_data = compute_bank_ke(bank_data, macro_global, macro_brazil)

    # Run all models
    ddm = compute_ddm(bank_data, ke_data)
    rim = compute_residual_income(bank_data, ke_data)
    jpbv = compute_justified_pbv(bank_data, ke_data)
    edcf = compute_equity_dcf(bank_data, ke_data)
    mult = compute_bank_multiples(bank_data)

    # Collect valid targets
    models = []
    if ddm and ddm.get("target_price"):
        tp = ddm["target_price"]
        # Sanity: target should be between 20% and 500% of current
        if current * 0.20 < tp < current * 5.0:
            models.append(("DDM", tp, 0.35))
    if rim and rim.get("target_price"):
        tp = rim["target_price"]
        if current * 0.20 < tp < current * 5.0:
            models.append(("RIM", tp, 0.25))
    if jpbv and jpbv.get("target_price"):
        tp = jpbv["target_price"]
        if current * 0.20 < tp < current * 5.0:
            models.append(("P/BV", tp, 0.25))
    if edcf and edcf.get("target_price"):
        tp = edcf["target_price"]
        if current * 0.20 < tp < current * 5.0:
            models.append(("EDCF", tp, 0.15))

    # Fallback to multiples if main models fail
    if not models and mult and mult.get("target_price"):
        tp = mult["target_price"]
        if tp > 0:
            models.append(("Mult", tp, 1.0))

    if not models:
        return {
            "target_price": None,
            "upside": None,
            "method": "N/A",
            "ke_data": ke_data,
        }

    # Normalize weights
    total_w = sum(w for _, _, w in models)
    final_tp = sum(tp * w / total_w for _, tp, w in models)

    upside = final_tp / current - 1

    # Clamp at ±50%
    if abs(upside) > 0.50:
        upside = np.sign(upside) * 0.50
        final_tp = current * (1 + upside)

    method_str = " + ".join(
        f"{name}({int(w / total_w * 100)}%)" for name, _, w in models
    )

    return {
        "target_price": round(final_tp, 2),
        "upside": round(upside, 4),
        "method": method_str,
        "ke_data": ke_data,
        "ddm": ddm,
        "rim": rim,
        "justified_pbv": jpbv,
        "equity_dcf": edcf,
        "multiples": mult,
    }
