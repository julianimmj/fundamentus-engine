"""
macro_global.py — Camada 1: Análise Macroeconômica Global
Fontes: Yahoo Finance (yields, VIX, DXY, commodities), World Bank API (GDP).
Sem dependência de FRED API.
"""
import logging
import numpy as np
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta
from engine.cache import get_cache

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Yahoo Finance tickers para macro global
# ─────────────────────────────────────────────────────────────
MACRO_TICKERS = {
    "us_10y":   "^TNX",       # US 10-Year Treasury Yield
    "us_2y":    "^IRX",       # US 13-Week Treasury (proxy short rate)
    "vix":      "^VIX",       # CBOE Volatility Index
    "dxy":      "DX-Y.NYB",   # US Dollar Index
    "brent":    "BZ=F",       # Brent Crude Oil Futures
    "wti":      "CL=F",       # WTI Crude Oil Futures
    "gold":     "GC=F",       # Gold Futures
    "copper":   "HG=F",       # Copper Futures
    "soybean":  "ZS=F",       # Soybean Futures
    "iron_ore": "TIO=F",      # Iron Ore (SGX)
    "sp500":    "^GSPC",      # S&P 500
    "nasdaq":   "^IXIC",      # Nasdaq Composite
}

# ─────────────────────────────────────────────────────────────
# World Bank API — GDP Growth
# ─────────────────────────────────────────────────────────────
WB_INDICATORS = {
    "gdp_world":    ("WLD", "NY.GDP.MKTP.KD.ZG"),
    "gdp_usa":      ("USA", "NY.GDP.MKTP.KD.ZG"),
    "gdp_china":    ("CHN", "NY.GDP.MKTP.KD.ZG"),
    "gdp_eurozone": ("EMU", "NY.GDP.MKTP.KD.ZG"),
    "cpi_usa":      ("USA", "FP.CPI.TOTL.ZG"),
}


def _fetch_wb_indicator(country, indicator, years=5):
    """Fetch latest value from World Bank API."""
    try:
        url = (
            f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
            f"?date={datetime.now().year - years}:{datetime.now().year}"
            f"&format=json&per_page=10"
        )
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if len(data) > 1 and data[1]:
                # Return most recent non-null value
                for entry in data[1]:
                    if entry.get("value") is not None:
                        return {
                            "value": float(entry["value"]),
                            "year": int(entry["date"]),
                        }
    except Exception as e:
        logger.warning(f"World Bank API error ({country}/{indicator}): {e}")
    return None


def _fetch_yf_macro(period="1y"):
    """Fetch all macro tickers from Yahoo Finance in one batch."""
    results = {}
    tickers_str = " ".join(MACRO_TICKERS.values())
    try:
        data = yf.download(
            tickers_str, period=period, interval="1d",
            group_by="ticker", progress=False, threads=True
        )
        for key, symbol in MACRO_TICKERS.items():
            try:
                if len(MACRO_TICKERS) == 1:
                    df = data
                else:
                    df = data[symbol] if symbol in data.columns.get_level_values(0) else None
                if df is not None and not df.empty:
                    df = df.dropna(subset=["Close"])
                    if not df.empty:
                        current = float(df["Close"].iloc[-1])
                        # Calculate returns
                        close = df["Close"].values
                        ret_1m = (close[-1] / close[-22] - 1) if len(close) > 22 else None
                        ret_3m = (close[-1] / close[-66] - 1) if len(close) > 66 else None
                        ret_6m = (close[-1] / close[-132] - 1) if len(close) > 132 else None
                        ret_12m = (close[-1] / close[0] - 1) if len(close) > 200 else None
                        results[key] = {
                            "current": current,
                            "ret_1m": ret_1m,
                            "ret_3m": ret_3m,
                            "ret_6m": ret_6m,
                            "ret_12m": ret_12m,
                            "high_52w": float(df["Close"].max()),
                            "low_52w": float(df["Close"].min()),
                        }
            except Exception as e:
                logger.warning(f"Error processing {key} ({symbol}): {e}")
    except Exception as e:
        logger.warning(f"Yahoo Finance batch macro error: {e}")
    return results


def _score_component(value, thresholds, invert=False):
    """
    Score a value 0-100 based on thresholds list [(val, score), ...].
    Thresholds must be sorted ascending by val.
    If invert=True, lower values get higher scores.
    """
    if value is None:
        return 50  # neutral default
    if invert:
        for threshold, score in reversed(thresholds):
            if value >= threshold:
                return score
    else:
        for threshold, score in thresholds:
            if value <= threshold:
                return score
    return thresholds[-1][1] if not invert else thresholds[0][1]


def compute_global_macro_score(macro_data):
    """
    Compute a 0-100 score for global macro environment.
    Higher = more favorable for EM / Brazil equities.
    """
    scores = []
    weights = []

    # VIX: Lower = better for risk assets
    vix = macro_data.get("vix", {})
    if vix:
        vix_val = vix.get("current", 20)
        vix_score = _score_component(vix_val, [
            (12, 95), (15, 85), (18, 70), (22, 55), (28, 35), (35, 15), (100, 5)
        ], invert=True)
        scores.append(vix_score)
        weights.append(0.20)

    # DXY: Lower / falling = better for EM
    dxy = macro_data.get("dxy", {})
    if dxy:
        dxy_ret = dxy.get("ret_3m", 0) or 0
        dxy_score = _score_component(dxy_ret * 100, [
            (-5, 90), (-2, 75), (0, 60), (2, 40), (5, 20), (10, 5)
        ], invert=True)
        scores.append(dxy_score)
        weights.append(0.15)

    # Commodities (Brent + Iron Ore): Higher / rising = better for Brazil
    for comm_key, w in [("brent", 0.12), ("iron_ore", 0.10), ("soybean", 0.08)]:
        comm = macro_data.get(comm_key, {})
        if comm:
            comm_ret = comm.get("ret_3m", 0) or 0
            comm_score = _score_component(comm_ret * 100, [
                (-15, 10), (-5, 30), (0, 50), (5, 70), (15, 90)
            ])
            scores.append(comm_score)
            weights.append(w)

    # US 10Y yield: Stable/falling = better for EM
    us10y = macro_data.get("us_10y", {})
    if us10y:
        y_val = us10y.get("current", 4.0)
        y_score = _score_component(y_val, [
            (2.5, 90), (3.5, 75), (4.0, 60), (4.5, 40), (5.0, 25), (6.0, 10)
        ], invert=True)
        scores.append(y_score)
        weights.append(0.15)

    # S&P 500 momentum: Rising = risk-on = favorable
    sp500 = macro_data.get("sp500", {})
    if sp500:
        sp_ret = sp500.get("ret_3m", 0) or 0
        sp_score = _score_component(sp_ret * 100, [
            (-10, 15), (-3, 35), (0, 50), (5, 70), (10, 85)
        ])
        scores.append(sp_score)
        weights.append(0.10)

    # GDP growth (if available)
    gdp = macro_data.get("gdp_world", {})
    if gdp and gdp.get("value") is not None:
        gdp_score = _score_component(gdp["value"], [
            (1, 20), (2, 40), (3, 60), (4, 80), (5, 90)
        ])
        scores.append(gdp_score)
        weights.append(0.10)

    if not scores:
        return 50.0

    # Normalize weights
    total_w = sum(weights)
    score = sum(s * w / total_w for s, w in zip(scores, weights))
    return round(min(100, max(0, score)), 1)


def fetch_global_macro(use_cache=True):
    """
    Main function: fetch all global macro data and compute score.
    Returns dict with raw data + computed score.
    """
    cache = get_cache()
    cache_key = "global_macro"

    if use_cache:
        cached = cache.get(cache_key, category="macro")
        if cached:
            logger.info("Global macro loaded from cache")
            return cached

    logger.info("Fetching global macro data...")
    result = {"timestamp": datetime.now().isoformat(), "indicators": {}}

    # Yahoo Finance macro
    yf_data = _fetch_yf_macro(period="1y")
    result["indicators"].update(yf_data)

    # World Bank GDP
    for key, (country, indicator) in WB_INDICATORS.items():
        wb_val = _fetch_wb_indicator(country, indicator)
        if wb_val:
            result["indicators"][key] = wb_val

    # Compute score
    result["score"] = compute_global_macro_score(result["indicators"])

    # Summary for display
    result["summary"] = _build_summary(result["indicators"], result["score"])

    cache.set(cache_key, result, category="macro")
    return result


def _build_summary(indicators, score):
    """Build human-readable summary of global macro conditions."""
    lines = []

    vix = indicators.get("vix", {}).get("current")
    if vix:
        level = "baixo (risk-on)" if vix < 18 else "elevado (cautela)" if vix > 25 else "moderado"
        lines.append(f"VIX em {vix:.1f} — nível {level}")

    us10y = indicators.get("us_10y", {}).get("current")
    if us10y:
        lines.append(f"Treasury 10Y em {us10y:.2f}%")

    dxy = indicators.get("dxy", {})
    if dxy:
        dxy_ret = dxy.get("ret_3m")
        if dxy_ret is not None:
            direction = "fortalecendo" if dxy_ret > 0.01 else "enfraquecendo" if dxy_ret < -0.01 else "estável"
            lines.append(f"Dólar Index (DXY) {direction} ({dxy_ret*100:+.1f}% 3m)")

    brent = indicators.get("brent", {}).get("current")
    if brent:
        lines.append(f"Brent a US$ {brent:.1f}/bbl")

    iron = indicators.get("iron_ore", {}).get("current")
    if iron:
        lines.append(f"Minério de ferro a US$ {iron:.1f}/ton")

    if score >= 70:
        outlook = "🟢 Ambiente global FAVORÁVEL para ativos brasileiros"
    elif score >= 50:
        outlook = "🟡 Ambiente global NEUTRO"
    else:
        outlook = "🔴 Ambiente global DESFAVORÁVEL — cautela"

    return {"outlook": outlook, "details": lines}
