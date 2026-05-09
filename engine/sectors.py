"""
sectors.py — Camada 3: Análise Setorial
Classifica ativos por setor, calcula métricas agregadas e determina
setores em overweight/underweight com base no cenário macro.
"""
import logging
import numpy as np
import pandas as pd
from engine.config import SECTORS, TICKER_SECTOR, get_sector_name, get_tickers_by_sector

logger = logging.getLogger(__name__)


def classify_ticker(ticker):
    """Return (sector_key, sector_name) for a ticker."""
    sector_key = TICKER_SECTOR.get(ticker, "outros")
    return sector_key, get_sector_name(sector_key)


def compute_sector_metrics(fundamentals_dict):
    """
    Compute aggregate metrics per sector from individual company fundamentals.
    
    Args:
        fundamentals_dict: dict of {ticker: {roe, roic, margin_ebitda, ...}}
    
    Returns:
        DataFrame with sector-level metrics.
    """
    rows = []
    sector_tickers = {}

    # Group tickers by sector
    for ticker, data in fundamentals_dict.items():
        sector_key = TICKER_SECTOR.get(ticker, "outros")
        if sector_key not in sector_tickers:
            sector_tickers[sector_key] = []
        sector_tickers[sector_key].append(data)

    for sector_key, companies in sector_tickers.items():
        if not companies:
            continue
        df = pd.DataFrame(companies)
        metrics = {
            "sector_key": sector_key,
            "sector_name": get_sector_name(sector_key),
            "n_companies": len(companies),
            "roe_median": _safe_median(df, "roe"),
            "roic_median": _safe_median(df, "roic"),
            "margin_ebitda_median": _safe_median(df, "margin_ebitda"),
            "margin_net_median": _safe_median(df, "margin_net"),
            "leverage_median": _safe_median(df, "net_debt_ebitda"),
            "revenue_cagr_median": _safe_median(df, "revenue_cagr_3y"),
            "ev_ebitda_median": _safe_median(df, "ev_ebitda"),
            "pe_median": _safe_median(df, "pe_ratio"),
            "dy_median": _safe_median(df, "dividend_yield"),
        }
        rows.append(metrics)

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _safe_median(df, col):
    """Compute median ignoring NaN, return None if not enough data."""
    if col in df.columns:
        vals = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(vals) >= 1:
            return round(float(vals.median()), 4)
    return None


def score_sector_alignment(sector_key, macro_global, macro_brazil):
    """
    Score 0-100 how well a sector aligns with current macro conditions.
    
    Uses sector sensitivities to juros, commodities, câmbio.
    """
    sector_info = SECTORS.get(sector_key)
    if not sector_info:
        return 50.0

    sens = sector_info.get("sensitivity", {})
    score = 50.0  # Start neutral

    # ── Interest rate sensitivity ──
    # If sector is interest-rate sensitive: low/falling rates = good
    juros_sens = sens.get("juros", 0.5)
    selic = macro_brazil.get("indicators", {}).get("selic_meta", 12)
    if selic is not None:
        if selic < 10:
            juros_boost = 20 * juros_sens  # Low rates help rate-sensitive sectors
        elif selic < 12:
            juros_boost = 5 * juros_sens
        elif selic < 14:
            juros_boost = -5 * juros_sens
        else:
            juros_boost = -15 * juros_sens
        # For banks, higher rates can boost NIM (inverted relationship)
        if sector_key == "bancos":
            juros_boost = -juros_boost * 0.5
        score += juros_boost

    # ── Commodity sensitivity ──
    comm_sens = sens.get("commodities", 0.5)
    global_ind = macro_global.get("indicators", {})
    brent_ret = global_ind.get("brent", {}).get("ret_3m", 0) or 0
    iron_ret = global_ind.get("iron_ore", {}).get("ret_3m", 0) or 0
    avg_comm_ret = (brent_ret + iron_ret) / 2

    if avg_comm_ret > 0.05:
        comm_boost = 15 * comm_sens
    elif avg_comm_ret > 0:
        comm_boost = 5 * comm_sens
    elif avg_comm_ret > -0.05:
        comm_boost = -5 * comm_sens
    else:
        comm_boost = -15 * comm_sens
    score += comm_boost

    # ── FX sensitivity ──
    cambio_sens = sens.get("cambio", 0.5)
    usd = macro_brazil.get("indicators", {}).get("usdbrl", {})
    usd_ret = usd.get("ret_3m", 0) if isinstance(usd, dict) else 0
    usd_ret = usd_ret or 0

    # For exporters: BRL depreciation (usd_ret > 0) = good
    # For importers/domestic: BRL appreciation = good
    if sector_key in ["mineracao", "petroleo", "papel_celulose", "agro", "alimentos"]:
        # Exporters benefit from weaker BRL
        fx_boost = usd_ret * 100 * cambio_sens
    else:
        # Domestic sectors benefit from stronger BRL
        fx_boost = -usd_ret * 100 * cambio_sens
    score += min(15, max(-15, fx_boost))

    # ── Global risk appetite (for BDRs) ──
    if sector_key.startswith("bdr_"):
        vix = global_ind.get("vix", {}).get("current", 20)
        if vix < 15:
            score += 10
        elif vix > 25:
            score -= 10

        sp_ret = global_ind.get("sp500", {}).get("ret_3m", 0) or 0
        score += min(10, max(-10, sp_ret * 50))

    return round(min(100, max(0, score)), 1)


def compute_all_sector_scores(macro_global, macro_brazil):
    """
    Compute alignment scores for all sectors.
    Returns dict of {sector_key: score}.
    """
    scores = {}
    for sector_key in SECTORS:
        scores[sector_key] = score_sector_alignment(
            sector_key, macro_global, macro_brazil
        )
    return scores


def classify_sectors(sector_scores):
    """
    Classify sectors as overweight, neutral, or underweight.
    Returns dict with {sector_key: {"score": x, "rating": "OW/N/UW"}}.
    """
    result = {}
    for sector_key, score in sector_scores.items():
        if score >= 65:
            rating = "Overweight"
        elif score >= 40:
            rating = "Neutral"
        else:
            rating = "Underweight"
        result[sector_key] = {
            "score": score,
            "rating": rating,
            "name": get_sector_name(sector_key),
        }
    return result
