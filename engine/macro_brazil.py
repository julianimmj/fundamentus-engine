"""
macro_brazil.py — Camada 2: Análise Macroeconômica Brasil
Fontes: API BCB (SGS/Olinda), Yahoo Finance (IBOV, câmbio).
"""
import logging
import numpy as np
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime, timedelta
from engine.cache import get_cache

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# BCB SGS Series IDs
# ─────────────────────────────────────────────────────────────
BCB_SERIES = {
    "selic_meta":       432,
    "cdi":              12,
    "ipca_mensal":      433,
    "ipca_12m":         13522,
    "igpm_mensal":      189,
    "cambio_ptax":      1,
    "divida_pib":       13762,
    "resultado_primario": 5793,
    "balanca_comercial":  22707,
}


def _fetch_bcb_sgs(series_id, last_n=30):
    """Fetch data from BCB SGS API."""
    try:
        end = datetime.now().strftime("%d/%m/%Y")
        start = (datetime.now() - timedelta(days=last_n * 35)).strftime("%d/%m/%Y")
        url = (
            f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series_id}"
            f"/dados?formato=json&dataInicial={start}&dataFinal={end}"
        )
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                df = pd.DataFrame(data)
                df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
                df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
                df = df.dropna(subset=["valor"]).sort_values("data")
                return df
    except Exception as e:
        logger.warning(f"BCB SGS error (series {series_id}): {e}")
    return pd.DataFrame()


def _fetch_focus_expectations():
    """Fetch BCB Focus market expectations (Olinda API)."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        indicators = {
            "IPCA": "IPCA",
            "Selic": "Selic",
            "PIB Total": "PIB",
            "Câmbio": "Cambio",
        }
        results = {}
        for indicator, key in indicators.items():
            url = (
                f"https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/"
                f"odata/ExpectativasMercadoAnuais?"
                f"$filter=Indicador eq '{indicator}' and Data ge '{today}'"
                f"&$top=10&$orderby=Data desc&$format=json"
            )
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json().get("value", [])
                if data:
                    # Get latest consensus for current and next year
                    current_year = datetime.now().year
                    for entry in data:
                        yr = entry.get("DataReferencia", current_year)
                        median = entry.get("Mediana")
                        if median is not None:
                            results[f"{key}_{yr}"] = float(median)
                            break
        return results
    except Exception as e:
        logger.warning(f"Focus expectations error: {e}")
    return {}


def _fetch_brazil_yf():
    """Fetch IBOV and USD/BRL from Yahoo Finance."""
    results = {}
    try:
        tickers = {"ibov": "^BVSP", "usdbrl": "BRL=X"}
        data = yf.download(
            " ".join(tickers.values()),
            period="1y", interval="1d",
            group_by="ticker", progress=False, threads=True
        )
        for key, symbol in tickers.items():
            try:
                df = data[symbol] if symbol in data.columns.get_level_values(0) else data
                if df is not None and not df.empty:
                    df = df.dropna(subset=["Close"])
                    close = df["Close"].values
                    current = float(close[-1])
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
                    }
            except Exception as e:
                logger.warning(f"YF Brazil error ({key}): {e}")
    except Exception as e:
        logger.warning(f"YF Brazil batch error: {e}")
    return results


def _get_latest_value(df):
    """Get the latest value from a BCB SGS DataFrame."""
    if df is not None and not df.empty:
        return float(df["valor"].iloc[-1])
    return None


def compute_brazil_macro_score(macro_data):
    """
    Compute 0-100 score for Brazil macro environment.
    Higher = more favorable for equities.
    """
    scores = []
    weights = []

    # Selic: Lower / falling = better for equities
    selic = macro_data.get("selic_meta")
    if selic is not None:
        selic_score = 90 if selic < 8 else 75 if selic < 10 else 55 if selic < 12 else 35 if selic < 14 else 15
        scores.append(selic_score)
        weights.append(0.25)

    # IPCA 12m: Lower = better
    ipca = macro_data.get("ipca_12m")
    if ipca is not None:
        ipca_score = 90 if ipca < 3.5 else 75 if ipca < 4.5 else 55 if ipca < 6 else 35 if ipca < 8 else 15
        scores.append(ipca_score)
        weights.append(0.20)

    # Câmbio (USD/BRL): Stable/falling = better
    usd = macro_data.get("usdbrl", {})
    if isinstance(usd, dict):
        usd_ret = usd.get("ret_3m", 0) or 0
        usd_score = 85 if usd_ret < -0.05 else 70 if usd_ret < -0.01 else 55 if usd_ret < 0.02 else 35 if usd_ret < 0.05 else 15
        scores.append(usd_score)
        weights.append(0.15)

    # Dívida/PIB: Lower = better
    divida = macro_data.get("divida_pib")
    if divida is not None:
        div_score = 85 if divida < 60 else 65 if divida < 75 else 45 if divida < 85 else 25
        scores.append(div_score)
        weights.append(0.10)

    # IBOV momentum
    ibov = macro_data.get("ibov", {})
    if isinstance(ibov, dict):
        ibov_ret = ibov.get("ret_3m", 0) or 0
        ibov_score = 85 if ibov_ret > 0.10 else 70 if ibov_ret > 0.03 else 50 if ibov_ret > -0.03 else 30 if ibov_ret > -0.10 else 15
        scores.append(ibov_score)
        weights.append(0.15)

    # Focus expectations (IPCA expectativa < meta = bom)
    focus = macro_data.get("focus", {})
    if focus:
        ipca_exp = focus.get(f"IPCA_{datetime.now().year}")
        if ipca_exp is not None:
            focus_score = 80 if ipca_exp < 4 else 60 if ipca_exp < 5 else 40 if ipca_exp < 6.5 else 20
            scores.append(focus_score)
            weights.append(0.15)

    if not scores:
        return 50.0

    total_w = sum(weights)
    score = sum(s * w / total_w for s, w in zip(scores, weights))
    return round(min(100, max(0, score)), 1)


def fetch_brazil_macro(use_cache=True):
    """
    Main function: fetch all Brazil macro data and compute score.
    """
    cache = get_cache()
    cache_key = "brazil_macro"

    if use_cache:
        cached = cache.get(cache_key, category="macro")
        if cached:
            logger.info("Brazil macro loaded from cache")
            return cached

    logger.info("Fetching Brazil macro data...")
    result = {"timestamp": datetime.now().isoformat(), "indicators": {}}

    # BCB SGS data
    for key, series_id in BCB_SERIES.items():
        df = _fetch_bcb_sgs(series_id, last_n=24)
        val = _get_latest_value(df)
        if val is not None:
            result["indicators"][key] = val

    # Focus expectations
    focus = _fetch_focus_expectations()
    if focus:
        result["indicators"]["focus"] = focus

    # Yahoo Finance (IBOV, USD/BRL)
    yf_data = _fetch_brazil_yf()
    result["indicators"].update(yf_data)

    # Compute score
    result["score"] = compute_brazil_macro_score(result["indicators"])

    # Summary
    result["summary"] = _build_brazil_summary(result["indicators"], result["score"])

    cache.set(cache_key, result, category="macro")
    return result


def _build_brazil_summary(indicators, score):
    """Build human-readable summary."""
    lines = []

    selic = indicators.get("selic_meta")
    if selic:
        lines.append(f"Selic Meta: {selic:.2f}% a.a.")

    ipca = indicators.get("ipca_12m")
    if ipca:
        lines.append(f"IPCA 12m acum: {ipca:.2f}%")

    usd = indicators.get("usdbrl", {})
    if isinstance(usd, dict) and usd.get("current"):
        lines.append(f"USD/BRL: R$ {usd['current']:.2f}")

    ibov = indicators.get("ibov", {})
    if isinstance(ibov, dict) and ibov.get("current"):
        lines.append(f"IBOV: {ibov['current']:,.0f} pts")

    divida = indicators.get("divida_pib")
    if divida:
        lines.append(f"Dívida Bruta/PIB: {divida:.1f}%")

    if score >= 65:
        outlook = "🟢 Macro Brasil FAVORÁVEL para renda variável"
    elif score >= 45:
        outlook = "🟡 Macro Brasil NEUTRO"
    else:
        outlook = "🔴 Macro Brasil DESFAVORÁVEL — postura defensiva"

    return {"outlook": outlook, "details": lines}
