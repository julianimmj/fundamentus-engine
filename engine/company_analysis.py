"""
company_analysis.py — Camada 4a: Análise fundamentalista por ativo
Coleta dados via yfinance, calcula indicadores, faz projeções 5 anos.
"""
import logging
import numpy as np
import pandas as pd
import yfinance as yf
from engine.cache import get_cache
from engine.config import TICKER_SECTOR, PROJECTION_YEARS

logger = logging.getLogger(__name__)


def fetch_company_data(ticker, use_cache=True):
    """
    Fetch all available fundamental data for a ticker from yfinance.
    Returns dict with raw data + computed indicators.
    """
    cache = get_cache()
    cache_key = f"company_{ticker}"

    if use_cache:
        cached = cache.get(cache_key, category="fundamentals")
        if cached:
            return cached

    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        # Basic info
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
            "free_float": info.get("floatShares"),
        }

        # ── Financial Statements ──
        income = _safe_financials(stock, "income_stmt")
        balance = _safe_financials(stock, "balance_sheet")
        cashflow = _safe_financials(stock, "cashflow")

        income_q = _safe_financials(stock, "quarterly_income_stmt")
        balance_q = _safe_financials(stock, "quarterly_balance_sheet")
        cashflow_q = _safe_financials(stock, "quarterly_cashflow")

        # ── Compute Indicators ──
        indicators = _compute_indicators(info, income, balance, cashflow)
        result.update(indicators)

        # ── Growth metrics ──
        growth = _compute_growth(income)
        result.update(growth)

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

        # ── Currency/scale sanity check ──
        # yfinance sometimes returns financials in different scales for .SA stocks
        mcap = result.get("market_cap")
        rev = result.get("revenue_latest")
        ebitda = result.get("ebitda_latest")
        if mcap and rev and rev > 0 and mcap > 0:
            ev_revenue = mcap / rev
            # If EV/Revenue > 50, financials might be in thousands (need 1000x)
            if ev_revenue > 50 and not TICKER_SECTOR.get(ticker, "").startswith("bdr_"):
                correction = 1000
                for key in ["revenue_latest", "ebitda_latest", "net_income_latest",
                            "operating_cashflow", "fcf", "capex", "interest_expense",
                            "total_debt", "cash", "net_debt", "equity", "total_assets"]:
                    if result.get(key):
                        result[key] = result[key] * correction
                if result.get("net_debt") is not None and result.get("ebitda_latest"):
                    ebitda_v = result["ebitda_latest"]
                    if ebitda_v > 0:
                        result["net_debt_ebitda"] = result["net_debt"] / ebitda_v
                logger.info(f"{ticker}: applied {correction}x scale correction to financials")

        # ── Projections ──
        projections = _compute_projections(result, income, balance)
        result["projections"] = projections

        # ── Store raw financials summary ──
        result["has_financials"] = income is not None and not income.empty

        cache.set(cache_key, result, category="fundamentals")
        return result

    except Exception as e:
        logger.warning(f"Error fetching {ticker}: {e}")
        return {"ticker": ticker, "error": str(e), "has_financials": False}


def _safe_financials(stock, attr):
    """Safely get financial statements."""
    try:
        df = getattr(stock, attr, None)
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
    return pd.DataFrame()


def _safe_get(df, row_labels, col_idx=0):
    """Safely extract a value from financial statement DataFrame."""
    if df is None or df.empty:
        return None
    for label in (row_labels if isinstance(row_labels, list) else [row_labels]):
        if label in df.index:
            try:
                val = df.iloc[df.index.get_loc(label), col_idx]
                if pd.notna(val):
                    return float(val)
            except Exception:
                pass
    return None


def _compute_indicators(info, income, balance, cashflow):
    """Compute fundamental indicators from financial statements."""
    ind = {}

    # ── From info dict ──
    ind["pe_ratio"] = info.get("trailingPE") or info.get("forwardPE")
    ind["pb_ratio"] = info.get("priceToBook")
    ind["ev_ebitda"] = info.get("enterpriseToEbitda")
    ind["ev_revenue"] = info.get("enterpriseToRevenue")
    ind["dividend_yield"] = info.get("dividendYield")
    ind["payout_ratio"] = info.get("payoutRatio")
    ind["roe"] = info.get("returnOnEquity")
    ind["roa"] = info.get("returnOnAssets")
    ind["debt_to_equity"] = info.get("debtToEquity")
    ind["current_ratio"] = info.get("currentRatio")
    ind["revenue_growth"] = info.get("revenueGrowth")
    ind["earnings_growth"] = info.get("earningsGrowth")
    ind["profit_margins"] = info.get("profitMargins")
    ind["operating_margins"] = info.get("operatingMargins")
    ind["gross_margins"] = info.get("grossMargins")

    # ── From statements ──
    if income is not None and not income.empty:
        revenue = _safe_get(income, ["Total Revenue", "Operating Revenue"])
        ebitda = _safe_get(income, ["EBITDA", "Normalized EBITDA"])
        net_income = _safe_get(income, ["Net Income", "Net Income Common Stockholders"])
        gross_profit = _safe_get(income, ["Gross Profit"])
        op_income = _safe_get(income, ["Operating Income", "EBIT"])
        interest = _safe_get(income, ["Interest Expense", "Net Interest Income"])

        if revenue and revenue > 0:
            ind["margin_gross"] = gross_profit / revenue if gross_profit else ind.get("gross_margins")
            ind["margin_ebitda"] = ebitda / revenue if ebitda else ind.get("operating_margins")
            ind["margin_net"] = net_income / revenue if net_income else ind.get("profit_margins")
            ind["margin_op"] = op_income / revenue if op_income else None

        ind["revenue_latest"] = revenue
        ind["ebitda_latest"] = ebitda
        ind["net_income_latest"] = net_income
        ind["interest_expense"] = interest

    if balance is not None and not balance.empty:
        total_debt = _safe_get(balance, ["Total Debt", "Long Term Debt"])
        cash = _safe_get(balance, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"])
        equity = _safe_get(balance, ["Stockholders Equity", "Total Equity Gross Minority Interest"])
        total_assets = _safe_get(balance, ["Total Assets"])

        ind["total_debt"] = total_debt
        ind["cash"] = cash
        ind["net_debt"] = (total_debt - cash) if total_debt and cash else None
        ind["equity"] = equity
        ind["total_assets"] = total_assets

        ebitda_val = ind.get("ebitda_latest")
        if ind["net_debt"] is not None and ebitda_val and ebitda_val > 0:
            ind["net_debt_ebitda"] = ind["net_debt"] / ebitda_val

    # ── ROIC ──
    if income is not None and not income.empty and balance is not None and not balance.empty:
        nopat = _safe_get(income, ["Operating Income", "EBIT"])
        if nopat:
            nopat *= (1 - 0.34)  # After-tax NOPAT
        equity_val = ind.get("equity")
        debt_val = ind.get("total_debt")
        cash_val = ind.get("cash", 0) or 0
        if nopat and equity_val and debt_val:
            invested_capital = equity_val + debt_val - cash_val
            if invested_capital > 0:
                ind["roic"] = nopat / invested_capital

    # ── FCF ──
    if cashflow is not None and not cashflow.empty:
        op_cf = _safe_get(cashflow, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"])
        capex = _safe_get(cashflow, ["Capital Expenditure", "Purchase Of PPE"])
        if op_cf is not None:
            ind["operating_cashflow"] = op_cf
            if capex is not None:
                ind["fcf"] = op_cf + capex  # capex is negative in yfinance
                ind["capex"] = capex
                price = info.get("currentPrice") or info.get("regularMarketPrice")
                shares = info.get("sharesOutstanding")
                if price and shares and ind["fcf"] > 0:
                    ind["fcf_yield"] = ind["fcf"] / (price * shares)

    return ind


def _compute_growth(income):
    """Compute CAGR of revenue and earnings over available periods."""
    growth = {}
    if income is None or income.empty or len(income.columns) < 2:
        return growth

    # Revenue CAGR
    revenues = []
    for col_idx in range(min(5, len(income.columns))):
        rev = _safe_get(income, ["Total Revenue", "Operating Revenue"], col_idx)
        if rev and rev > 0:
            revenues.append(rev)

    if len(revenues) >= 2:
        n = len(revenues) - 1
        if revenues[-1] > 0 and revenues[0] > 0:
            growth["revenue_cagr_3y"] = (revenues[0] / revenues[-1]) ** (1 / n) - 1

    # Earnings CAGR
    earnings = []
    for col_idx in range(min(5, len(income.columns))):
        ni = _safe_get(income, ["Net Income", "Net Income Common Stockholders"], col_idx)
        if ni and ni > 0:
            earnings.append(ni)

    if len(earnings) >= 2:
        n = len(earnings) - 1
        if earnings[-1] > 0 and earnings[0] > 0:
            growth["earnings_cagr_3y"] = (earnings[0] / earnings[-1]) ** (1 / n) - 1

    return growth


def _compute_projections(company, income, balance):
    """
    Project key financials for next 5 years using historical trends
    and mean-reversion to sector averages.
    """
    proj = {"years": list(range(1, PROJECTION_YEARS + 1))}

    revenue = company.get("revenue_latest")
    if not revenue or revenue <= 0:
        return proj

    # Revenue growth rate — conservative cap at 12% Y1 (sell-side consensus rarely > 15%)
    hist_cagr = company.get("revenue_cagr_3y") or company.get("revenue_growth") or 0.05
    rev_growth = max(-0.05, min(0.12, hist_cagr))
    # Fade growth toward nominal GDP over projection period (faster fade)
    gdp_growth = 0.05  # Nominal GDP Brasil ~5% (2.5% real + 2.5% inflation target)
    fade_rates = [
        rev_growth + (gdp_growth - rev_growth) * ((i + 1) / PROJECTION_YEARS)
        for i in range(PROJECTION_YEARS)
    ]

    proj["revenue"] = []
    rev = revenue
    for g in fade_rates:
        rev *= (1 + g)
        proj["revenue"].append(round(rev))

    # EBITDA margin (converge toward current with slight mean reversion)
    margin = company.get("margin_ebitda") or company.get("operating_margins") or 0.15
    margin = max(0.05, min(0.60, margin))
    proj["ebitda"] = [round(r * margin) for r in proj["revenue"]]

    # Capex as % of revenue (historical or 5% default)
    capex_pct = 0.05
    if company.get("capex") and revenue:
        capex_pct = abs(company["capex"]) / revenue
        capex_pct = max(0.02, min(0.15, capex_pct))
    proj["capex"] = [round(-r * capex_pct) for r in proj["revenue"]]

    # D&A (approximate as 40% of capex)
    proj["depreciation"] = [round(abs(c) * 0.4) for c in proj["capex"]]

    # Tax rate
    tax = 0.34
    proj["nopat"] = [round(e * (1 - tax)) for e in proj["ebitda"]]

    # FCF = NOPAT + D&A - Capex - ΔWC (ΔWC approximated as 0 for simplicity)
    proj["fcff"] = [
        proj["nopat"][i] + proj["depreciation"][i] + proj["capex"][i]
        for i in range(PROJECTION_YEARS)
    ]

    proj["growth_rates"] = [round(g, 4) for g in fade_rates]

    return proj
