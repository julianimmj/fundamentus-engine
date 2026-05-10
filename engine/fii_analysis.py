"""
fii_analysis.py — Análise específica para Fundos Imobiliários (FIIs)
Calcula DY, P/VP, spread sobre CDI, consistência de dividendos.
"""
import logging
import numpy as np
import yfinance as yf
from engine.cache import get_cache
import requests
from bs4 import BeautifulSoup
from engine.config import FII_TYPES

logger = logging.getLogger(__name__)

def _scrape_pvp_fundamentus(ticker):
    """Fallback web scraper to get P/VP from Fundamentus when yfinance fails."""
    try:
        clean_ticker = ticker.replace(".SA", "")
        url = f"https://www.fundamentus.com.br/detalhes.php?papel={clean_ticker}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            spans = soup.find_all('span', class_='txt')
            for span in spans:
                if 'P/VP' in span.text:
                    td = span.find_parent('td')
                    if td:
                        next_td = td.find_next_sibling('td')
                        if next_td:
                            val_str = next_td.text.strip().replace(',', '.')
                            return float(val_str)
    except Exception as e:
        logger.debug(f"Scraper failed for {ticker}: {e}")
    return None

def analyze_fii(ticker, macro_brazil=None, use_cache=True):
    """
    Análise específica de FII.
    Retorna métricas adaptadas: DY, P/VP, spread CDI, tipo.
    """
    cache = get_cache()
    cache_key = f"fii_{ticker}"

    if use_cache:
        cached = cache.get(cache_key, category="fundamentals")
        if cached:
            return cached

    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        hist = stock.history(period="2y", interval="1d")

        result = {
            "ticker": ticker,
            "name": info.get("shortName") or info.get("longName") or ticker.replace(".SA", ""),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "market_cap": info.get("marketCap"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "fii_type": FII_TYPES.get(ticker, "outros"),
            "has_financials": True,
        }

        # ── P/VP ──
        nav = info.get("bookValue")  # NAV per share
        price = result["current_price"]
        if nav and price and nav > 0:
            result["p_vp"] = round(price / nav, 4)
        else:
            result["p_vp"] = info.get("priceToBook")
            
        if result.get("p_vp") is None:
            logger.info(f"yfinance missed P/VP for {ticker}, using scraper fallback.")
            result["p_vp"] = _scrape_pvp_fundamentus(ticker)

        # ── Dividend Yield (trailing 12m) ──
        # Prefer dividendRate / price (always correct) over dividendYield
        rate = info.get("dividendRate")
        if rate and price and price > 0 and rate > 0:
            dy = rate / price
            if dy < 0.60:
                result["dividend_yield"] = round(dy, 6)
            else:
                result["dividend_yield"] = None
        else:
            dy = info.get("dividendYield")
            if dy is not None and abs(dy) > 1.0:
                dy = dy / 100.0
            if dy and 0 < dy < 0.60:
                result["dividend_yield"] = round(dy, 6)
            else:
                result["dividend_yield"] = None

        # ── Dividends history for consistency ──
        dividends = stock.dividends
        if dividends is not None and len(dividends) > 0:
            # Last 12 months dividends
            from datetime import datetime, timedelta, timezone
            cutoff = datetime.now(timezone.utc) - timedelta(days=365)
            recent_divs = dividends[dividends.index >= cutoff]
            
            if len(recent_divs) > 0:
                total_div_12m = float(recent_divs.sum())
                if price and price > 0:
                    result["dy_calculated"] = round(total_div_12m / price, 4)
                
                # Consistency: coefficient of variation (lower = more consistent)
                if len(recent_divs) >= 4:
                    cv = float(recent_divs.std() / recent_divs.mean()) if recent_divs.mean() > 0 else 999
                    result["div_consistency"] = round(1 - min(1, cv), 4)  # 1 = very consistent
                    result["div_monthly_avg"] = round(float(recent_divs.mean()), 4)
                else:
                    result["div_consistency"] = 0.5

                # Annualized projected DY
                months_covered = max(1, len(recent_divs))
                annual_proj = total_div_12m * (12 / months_covered)
                if price and price > 0:
                    result["dy_projected"] = round(annual_proj / price, 4)

        # ── Spread over CDI ──
        cdi = None
        if macro_brazil:
            cdi = macro_brazil.get("indicators", {}).get("selic_meta")
        if cdi and result.get("dy_calculated"):
            result["spread_cdi"] = round(result["dy_calculated"] * 100 - cdi, 2)

        # ── Price momentum ──
        if hist is not None and not hist.empty:
            close = hist["Close"].values
            result["avg_volume_20d"] = float(hist["Volume"].tail(20).mean()) if "Volume" in hist else None
            result["ret_1m"] = float(close[-1] / close[-22] - 1) if len(close) > 22 else None
            result["ret_3m"] = float(close[-1] / close[-66] - 1) if len(close) > 66 else None
            result["ret_6m"] = float(close[-1] / close[-132] - 1) if len(close) > 132 else None
            result["ret_12m"] = float(close[-1] / close[0] - 1) if len(close) > 200 else None
            result["price_52w_high"] = float(hist["Close"].tail(252).max())
            result["price_52w_low"] = float(hist["Close"].tail(252).min())

        cache.set(cache_key, result, category="fundamentals")
        return result

    except Exception as e:
        logger.warning(f"FII analysis error for {ticker}: {e}")
        return {"ticker": ticker, "error": str(e), "has_financials": False}


def score_fii(fii_data, macro_brazil=None):
    """
    Score a FII 0-100 based on FII-specific criteria.
    Replaces the standard company scoring for FIIs.
    """
    score = 50.0  # Start neutral

    # P/VP: < 1.0 is attractive, > 1.1 is expensive
    p_vp = fii_data.get("p_vp")
    if p_vp is not None:
        if p_vp < 0.85:
            score += 15
        elif p_vp < 0.95:
            score += 10
        elif p_vp < 1.05:
            score += 0
        elif p_vp < 1.15:
            score -= 5
        else:
            score -= 10

    # DY: higher is better (relative to CDI)
    spread = fii_data.get("spread_cdi")
    if spread is not None:
        if spread > 4:
            score += 15
        elif spread > 2:
            score += 10
        elif spread > 0:
            score += 5
        else:
            score -= 10

    # Consistency of distributions
    consistency = fii_data.get("div_consistency", 0.5)
    score += (consistency - 0.5) * 20  # -10 to +10

    # Liquidity
    vol = fii_data.get("avg_volume_20d", 0) or 0
    if vol > 1_000_000:
        score += 5
    elif vol > 500_000:
        score += 2
    elif vol < 100_000:
        score -= 5

    # Macro alignment: falling rates = good for FIIs
    if macro_brazil:
        selic = macro_brazil.get("indicators", {}).get("selic_meta", 13)
        if selic < 10:
            score += 10
        elif selic < 12:
            score += 5
        elif selic > 14:
            score -= 10

    return round(min(100, max(0, score)), 1)
