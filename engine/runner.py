"""
runner.py — Orquestrador principal do pipeline Top-Down
Executa todas as camadas em sequência, com processamento paralelo para ativos.
"""
import logging
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from engine.config import get_all_tickers, get_ticker_type, TICKER_SECTOR, is_financial_institution
from engine.cache import get_cache
from engine.macro_global import fetch_global_macro
from engine.macro_brazil import fetch_brazil_macro
from engine.sectors import (
    compute_sector_metrics, compute_all_sector_scores,
    classify_sectors, classify_ticker
)
from engine.company_analysis import fetch_company_data
from engine.valuation import run_valuation
from engine.fii_analysis import analyze_fii, score_fii
from engine.bank_analysis import fetch_bank_data
from engine.bank_valuation import run_bank_valuation
from engine.scoring import compute_composite_score, classify_asset

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _process_single_ticker(ticker, macro_global, macro_brazil, sector_scores, use_cache=True):
    """Process a single ticker through the full pipeline."""
    try:
        ticker_type = get_ticker_type(ticker)
        sector_key = TICKER_SECTOR.get(ticker, "outros")
        is_fii = sector_key == "fii"
        is_bank = is_financial_institution(ticker)

        # ── Fetch data (3 pipelines: FII / Bank / Generic) ──
        fii_sc = None
        if is_fii:
            company = analyze_fii(ticker, macro_brazil, use_cache=use_cache)
            fii_sc = score_fii(company, macro_brazil)
        elif is_bank:
            company = fetch_bank_data(ticker, use_cache=use_cache)
        else:
            company = fetch_company_data(ticker, use_cache=use_cache)

        if company.get("error") and not company.get("current_price"):
            return None

        # ── Valuation (3 pipelines) ──
        if is_fii:
            valuation = {
                "target_price": None,
                "upside": None,
                "method": "FII-DY",
            }
            p_vp = company.get("p_vp")
            if p_vp and p_vp > 0:
                valuation["upside"] = round(1 / p_vp - 1, 4)
                if company.get("current_price"):
                    valuation["target_price"] = round(
                        company["current_price"] / p_vp, 2
                    )
        elif is_bank:
            valuation = run_bank_valuation(company, macro_global, macro_brazil)
        else:
            sect_met = _get_sector_medians(sector_key)
            valuation = run_valuation(company, macro_global, macro_brazil, sect_met)

        # ── Scoring ──
        macro_global_score = macro_global.get("score", 50)
        macro_brazil_score = macro_brazil.get("score", 50)
        sector_sc = sector_scores.get(sector_key, 50)

        score_data = compute_composite_score(
            company, valuation, macro_global_score,
            macro_brazil_score, sector_sc,
            is_fii=is_fii, fii_score=fii_sc,
            is_bank=is_bank
        )

        # ── Classification ──
        macro_combined = (macro_global_score + macro_brazil_score) / 2
        rating = classify_asset(score_data, valuation, macro_combined)

        # ── Build result row ──
        _, sector_name = classify_ticker(ticker)
        row = {
            "Ticker": ticker.replace(".SA", ""),
            "Nome": company.get("name", ""),
            "Tipo": ticker_type,
            "Setor": sector_name,
            "Preço": company.get("current_price"),
            "Target Price": valuation.get("target_price"),
            "Upside": valuation.get("upside"),
            "Score": score_data.get("score"),
            "Rating": rating,
            "ROE": company.get("roe"),
            "ROIC": company.get("roic"),
            "Margem EBITDA": company.get("margin_ebitda"),
            "Dív. Líq./EBITDA": company.get("net_debt_ebitda"),
            "P/L": company.get("pe_ratio"),
            "EV/EBITDA": company.get("ev_ebitda"),
            "Div. Yield": company.get("dividend_yield"),
            "Cresc. Receita": company.get("revenue_cagr_3y") or company.get("revenue_growth"),
            "Vol. Médio": company.get("avg_volume_20d"),
            "Ret. 3m": company.get("ret_3m"),
            "Ret. 6m": company.get("ret_6m"),
            "Score Macro": score_data.get("macro_score"),
            "Score Qualidade": score_data.get("quality_score"),
            "Score Valuation": score_data.get("valuation_score"),
            "Score Momentum": score_data.get("momentum_score"),
            "Score Governança": score_data.get("governance_score"),
            "Método Val.": valuation.get("method"),
        }

        # FII-specific columns
        if is_fii:
            row["P/VP"] = company.get("p_vp")
            row["Spread CDI"] = company.get("spread_cdi")
            row["Consist. Div."] = company.get("div_consistency")
            row["Tipo FII"] = company.get("fii_type")

        # Bank-specific columns
        if is_bank:
            row["NIM"] = company.get("nim")
            row["Cost/Income"] = company.get("cost_income")
            row["CET1 Proxy"] = company.get("cet1_proxy")
            row["NPL Proxy"] = company.get("npl_proxy")
            row["P/BV"] = company.get("pb_ratio")
            row["Cresc. Carteira"] = company.get("loan_growth")
            row["PDD/Lucro"] = company.get("pdd_lucro")
            # Data source transparency
            row["Fonte CET1"] = company.get("fonte_cet1", "Proxy")
            row["Fonte NPL"] = company.get("fonte_npl", "Proxy")
            row["Dados Ref."] = company.get("dados_regulatorios_data")
            row["Dados Fonte"] = company.get("dados_regulatorios_fonte", "Proxy")

        return row

    except Exception as e:
        logger.error(f"Error processing {ticker}: {e}")
        return None


# Simple sector medians cache (populated during run)
_sector_medians_cache = {}

def _get_sector_medians(sector_key):
    return _sector_medians_cache.get(sector_key, {})


def run_full_analysis(tickers=None, max_workers=8, use_cache=True, progress_callback=None):
    """
    Execute the complete Top-Down analysis pipeline.
    
    Args:
        tickers: list of tickers (default: all from config)
        max_workers: parallel workers for company analysis
        use_cache: use cached data when available
        progress_callback: callable(current, total, message) for UI updates
    
    Returns:
        dict with:
            - "macro_global": global macro data + score
            - "macro_brazil": brazil macro data + score
            - "sector_scores": sector alignment scores
            - "results": DataFrame with all assets scored and classified
            - "promissores": DataFrame filtered to Promissor rating
            - "neutros": DataFrame filtered to Neutro rating
            - "vies_ruim": DataFrame filtered to Viés Ruim rating
    """
    if tickers is None:
        tickers = get_all_tickers()

    total = len(tickers)
    logger.info(f"Starting full analysis for {total} tickers...")

    def _progress(current, msg=""):
        if progress_callback:
            progress_callback(current, total, msg)

    # ═══ STEP 1: Global Macro ═══
    _progress(0, "Buscando dados macro globais...")
    macro_global = fetch_global_macro(use_cache=use_cache)
    logger.info(f"Global macro score: {macro_global.get('score', 'N/A')}")

    # ═══ STEP 2: Brazil Macro ═══
    _progress(0, "Buscando dados macro Brasil...")
    macro_brazil = fetch_brazil_macro(use_cache=use_cache)
    logger.info(f"Brazil macro score: {macro_brazil.get('score', 'N/A')}")

    # ═══ STEP 3: Sector Scores ═══
    _progress(0, "Calculando scores setoriais...")
    sector_scores = compute_all_sector_scores(macro_global, macro_brazil)
    sector_classification = classify_sectors(sector_scores)

    # ═══ STEP 4: Process each ticker ═══
    results = []
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for ticker in tickers:
            future = executor.submit(
                _process_single_ticker,
                ticker, macro_global, macro_brazil, sector_scores, use_cache
            )
            futures[future] = ticker

        for future in as_completed(futures):
            completed += 1
            ticker = futures[future]
            _progress(completed, f"Processado: {ticker.replace('.SA', '')}")

            try:
                row = future.result()
                if row:
                    results.append(row)
            except Exception as e:
                logger.error(f"Future error for {ticker}: {e}")

    # ═══ STEP 5: Build DataFrame ═══
    if not results:
        logger.error("No results generated!")
        return {
            "macro_global": macro_global,
            "macro_brazil": macro_brazil,
            "sector_scores": sector_classification,
            "results": pd.DataFrame(),
            "promissores": pd.DataFrame(),
            "neutros": pd.DataFrame(),
            "vies_ruim": pd.DataFrame(),
        }

    df = pd.DataFrame(results)
    df = df.sort_values("Score", ascending=False).reset_index(drop=True)

    # ═══ STEP 6: Classify ═══
    promissores = df[df["Rating"] == "Promissor"].copy()
    neutros = df[df["Rating"] == "Neutro"].copy()
    vies_ruim = df[df["Rating"] == "Viés Ruim"].copy()

    logger.info(
        f"Analysis complete: {len(promissores)} Promissores, "
        f"{len(neutros)} Neutros, {len(vies_ruim)} Viés Ruim"
    )

    return {
        "macro_global": macro_global,
        "macro_brazil": macro_brazil,
        "sector_scores": sector_classification,
        "results": df,
        "promissores": promissores,
        "neutros": neutros,
        "vies_ruim": vies_ruim,
        "timestamp": pd.Timestamp.now().isoformat(),
    }
