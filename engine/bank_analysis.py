"""
bank_analysis.py — Módulo especializado para Instituições Financeiras
Extrai métricas bancárias: NIM, Cost/Income, NPL proxy, CET1 proxy, Loan Growth.
Projeta: carteira de crédito, NIM, provisões, PL, net income (5 anos).
Usa dados reais do BCB OLINDA API e FDIC BankFind quando disponíveis,
com fallback para proxies calculados via yfinance.
"""
import logging
import numpy as np
import pandas as pd
import yfinance as yf
from engine.cache import get_cache
from engine.config import TICKER_SECTOR, PROJECTION_YEARS
from engine.company_analysis import _safe_financials, _safe_get, _compute_dividend_yield

try:
    from engine.bcb_data import fetch_bcb_regulatory, BCB_CODES
except Exception:
    fetch_bcb_regulatory = None
    BCB_CODES = {}

try:
    from engine.fdic_data import fetch_fdic_regulatory, FDIC_CERTS
except Exception:
    fetch_fdic_regulatory = None
    FDIC_CERTS = {}

logger = logging.getLogger(__name__)


def fetch_bank_data(ticker, use_cache=True):
    """
    Fetch fundamental data optimized for banks/financial institutions.
    Returns dict with standard + bank-specific indicators.
    """
    cache = get_cache()
    cache_key = f"bank_{ticker}"

    if use_cache:
        cached = cache.get(cache_key, category="fundamentals")
        if cached:
            return cached

    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        result = {
            "ticker": ticker,
            "name": info.get("shortName") or info.get("longName") or ticker.replace(".SA", ""),
            "sector_yf": info.get("sector", ""),
            "industry_yf": info.get("industry", ""),
            "market_cap": info.get("marketCap"),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "currency": info.get("currency", "BRL"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "beta": info.get("beta"),
            "is_bank": True,
        }

        # Financial statements
        income = _safe_financials(stock, "income_stmt")
        balance = _safe_financials(stock, "balance_sheet")
        cashflow = _safe_financials(stock, "cashflow")

        # ── Standard ratios from info ──
        result["pe_ratio"] = info.get("trailingPE") or info.get("forwardPE")
        result["pb_ratio"] = info.get("priceToBook")
        result["dividend_yield"] = _compute_dividend_yield(info)
        result["payout_ratio"] = info.get("payoutRatio")
        if result["payout_ratio"] and result["payout_ratio"] > 1.5:
            result["payout_ratio"] = result["payout_ratio"] / 100.0

        # ── ROE / ROA from info (normalized) ──
        roe = info.get("returnOnEquity")
        if roe and abs(roe) > 1.5:
            roe = roe / 100.0
        result["roe"] = roe

        roa = info.get("returnOnAssets")
        if roa and abs(roa) > 0.15:
            roa = roa / 100.0
        result["roa"] = roa

        # ── Bank-specific metrics from statements (proxies) ──
        bank_metrics = _compute_bank_metrics(info, income, balance)
        result.update(bank_metrics)

        # ── Override with real regulatory data when available ──
        real_data = {}
        if fetch_bcb_regulatory and ticker in BCB_CODES:
            real_data = fetch_bcb_regulatory(ticker, use_cache=use_cache)
        elif fetch_fdic_regulatory and ticker in FDIC_CERTS:
            real_data = fetch_fdic_regulatory(ticker, use_cache=use_cache)

        if real_data:
            # Override proxy values with real data
            if "cet1_real" in real_data:
                result["cet1_proxy"] = real_data["cet1_real"]
                result["fonte_cet1"] = real_data.get("fonte_cet1", "Real")
            else:
                result["fonte_cet1"] = "Proxy"

            if "npl_real" in real_data:
                result["npl_proxy"] = real_data["npl_real"]
                result["fonte_npl"] = real_data.get("fonte_npl", "Real")
            else:
                result["fonte_npl"] = "Proxy"

            if "nim_real" in real_data:
                result["nim"] = real_data["nim_real"]

            if "cost_income_real" in real_data:
                result["cost_income"] = real_data["cost_income_real"]

            # Store reference date for UI transparency
            result["dados_regulatorios_data"] = (
                real_data.get("bcb_reference_date")
                or real_data.get("fdic_reference_date")
            )
            result["dados_regulatorios_fonte"] = (
                "BCB" if ticker in BCB_CODES else "FDIC"
            )
        else:
            result["fonte_cet1"] = "Proxy"
            result["fonte_npl"] = "Proxy"
            result["dados_regulatorios_fonte"] = "Proxy"
            result["dados_regulatorios_data"] = None

        # ── Price history for momentum ──
        hist = stock.history(period="1y", interval="1d")
        if hist is not None and not hist.empty:
            close = hist["Close"].values
            result["price_52w_high"] = float(hist["Close"].max())
            result["price_52w_low"] = float(hist["Close"].min())
            result["avg_volume_20d"] = float(hist["Volume"].tail(20).mean()) if "Volume" in hist else None
            result["ret_1m"] = float(close[-1] / close[-22] - 1) if len(close) > 22 else None
            result["ret_3m"] = float(close[-1] / close[-66] - 1) if len(close) > 66 else None
            result["ret_6m"] = float(close[-1] / close[-132] - 1) if len(close) > 132 else None
            result["ret_12m"] = float(close[-1] / close[0] - 1) if len(close) > 200 else None

        # ── Projections ──
        result["projections"] = _compute_bank_projections(result, income, balance)
        result["has_financials"] = income is not None and not income.empty

        cache.set(cache_key, result, category="fundamentals")
        return result

    except Exception as e:
        logger.warning(f"Error fetching bank data for {ticker}: {e}")
        return {"ticker": ticker, "error": str(e), "has_financials": False, "is_bank": True}


def _compute_bank_metrics(info, income, balance):
    """Compute bank-specific financial metrics."""
    m = {}

    if income is None or income.empty:
        return m

    # ── Net Interest Income ──
    nii = _safe_get(income, [
        "Net Interest Income", "Interest Income", "Net Interest Income After Provision"
    ])
    m["net_interest_income"] = nii

    # ── Total Revenue (banks) ──
    total_rev = _safe_get(income, ["Total Revenue", "Operating Revenue"])
    non_interest = _safe_get(income, [
        "Non Interest Income", "Other Non Interest Income", "Fee Income"
    ])
    m["revenue_latest"] = total_rev

    # ── Net Income ──
    net_income = _safe_get(income, ["Net Income", "Net Income Common Stockholders"])
    m["net_income_latest"] = net_income

    # ── Operating Expenses ──
    opex = _safe_get(income, [
        "Operating Expense", "Selling General And Administration",
        "General And Administrative Expense"
    ])
    m["operating_expense"] = opex

    # ── Provisions for Credit Losses ──
    provisions = _safe_get(income, [
        "Provision For Doubtful Accounts", "Credit Losses Provision",
        "Loan Loss Provision", "Impairment Of Capital Assets"
    ])
    m["provisions"] = provisions

    # ── NIM (Net Interest Margin) ──
    # NIM = NII / Earning Assets. Proxy: NII / Total Assets
    if balance is not None and not balance.empty:
        total_assets = _safe_get(balance, ["Total Assets"])
        m["total_assets"] = total_assets
        equity = _safe_get(balance, [
            "Stockholders Equity", "Total Equity Gross Minority Interest"
        ])
        m["equity"] = equity
        
        # Total Loans (proxy for earning assets)
        loans = _safe_get(balance, [
            "Net Loan", "Gross Loans", "Loans And Advances To Customers",
            "Loans Receivable", "Receivables", "Total Non Current Assets"
        ])
        m["total_loans"] = loans

        if nii and total_assets and total_assets > 0:
            m["nim"] = round(nii / total_assets, 4)

        # ── CET1 Proxy (Equity / Total Assets) ──
        if equity and total_assets and total_assets > 0:
            m["cet1_proxy"] = round(equity / total_assets, 4)

        # ── NPL Proxy (Provisions / Loans) ──
        if provisions and loans and loans > 0:
            m["npl_proxy"] = round(abs(provisions) / loans, 4)
        elif provisions and total_assets and total_assets > 0:
            m["npl_proxy"] = round(abs(provisions) / total_assets, 4)

    # ── Cost/Income Ratio ──
    if opex and total_rev and total_rev > 0:
        m["cost_income"] = round(abs(opex) / total_rev, 4)
    elif opex and nii and nii > 0:
        m["cost_income"] = round(abs(opex) / nii, 4)

    # ── PDD/Lucro (Provisions / Net Income) ──
    if provisions and net_income and net_income > 0:
        m["pdd_lucro"] = round(abs(provisions) / net_income, 4)

    # ── Loan Growth (YoY) ──
    if balance is not None and not balance.empty and len(balance.columns) >= 2:
        loans_t0 = _safe_get(balance, [
            "Net Loan", "Gross Loans", "Loans Receivable", "Receivables"
        ], 0)
        loans_t1 = _safe_get(balance, [
            "Net Loan", "Gross Loans", "Loans Receivable", "Receivables"
        ], 1)
        if loans_t0 and loans_t1 and loans_t1 > 0:
            m["loan_growth"] = round(loans_t0 / loans_t1 - 1, 4)

    # ── Revenue Growth ──
    if income is not None and len(income.columns) >= 2:
        rev_t0 = _safe_get(income, ["Total Revenue", "Operating Revenue"], 0)
        rev_t1 = _safe_get(income, ["Total Revenue", "Operating Revenue"], 1)
        if rev_t0 and rev_t1 and rev_t1 > 0:
            m["revenue_growth"] = round(rev_t0 / rev_t1 - 1, 4)
            m["revenue_cagr_3y"] = m["revenue_growth"]  # Simplified for banks

    # ── Earnings Growth ──
    if income is not None and len(income.columns) >= 2:
        ni_t0 = _safe_get(income, ["Net Income"], 0)
        ni_t1 = _safe_get(income, ["Net Income"], 1)
        if ni_t0 and ni_t1 and ni_t1 > 0:
            m["earnings_growth"] = round(ni_t0 / ni_t1 - 1, 4)

    return m


def _compute_bank_projections(bank_data, income, balance):
    """
    Project bank financials for 5 years.
    
    Bank projections differ from corporates:
    - Revenue = Earning Assets × NIM + Non-Interest Income
    - Key driver is equity growth (retained earnings) not revenue
    - Provisions tied to macro cycle and loan portfolio quality
    """
    proj = {"years": list(range(1, PROJECTION_YEARS + 1))}

    net_income = bank_data.get("net_income_latest")
    equity = bank_data.get("equity")
    roe = bank_data.get("roe")

    if not net_income or not equity or equity <= 0:
        return proj

    if not roe or roe <= 0:
        roe = net_income / equity if equity > 0 else 0.12

    # Retention ratio (1 - payout)
    payout = bank_data.get("payout_ratio") or 0.35
    payout = max(0.20, min(0.80, payout))
    retention = 1 - payout

    # ROE fade: converge to sustainable 14% over projection period
    sustainable_roe = 0.14
    roe_path = [
        roe + (sustainable_roe - roe) * ((i + 1) / PROJECTION_YEARS)
        for i in range(PROJECTION_YEARS)
    ]

    # Project equity and net income
    proj_equity = [equity]
    proj_ni = []
    proj_dividends = []

    for i, target_roe in enumerate(roe_path):
        prev_eq = proj_equity[-1]
        ni = prev_eq * target_roe
        div = ni * payout
        new_eq = prev_eq + ni * retention

        proj_ni.append(round(ni))
        proj_dividends.append(round(div))
        proj_equity.append(round(new_eq))

    proj["net_income"] = proj_ni
    proj["dividends"] = proj_dividends
    proj["equity"] = proj_equity[1:]  # Remove initial equity
    proj["roe_path"] = [round(r, 4) for r in roe_path]

    # FCFE = Net Income - ΔEquity (equity needed to sustain growth)
    proj["fcfe"] = [
        proj_ni[i] - (proj_equity[i + 1] - proj_equity[i])
        for i in range(PROJECTION_YEARS)
    ]

    # Alias for compatibility with valuation pipeline
    proj["fcff"] = proj_dividends  # For DDM: dividends are the cash flows
    proj["growth_rates"] = [round(r, 4) for r in roe_path]

    return proj
