"""
scoring.py — Camada 5: Score Composto (0-100) e Classificação Final
Pondera: 30% Macro + 25% Qualidade + 25% Valuation + 15% Momentum + 5% Governança
"""
import logging
import numpy as np
from engine.config import (
    SCORE_WEIGHTS, THRESHOLDS, TICKER_SECTOR,
    TICKER_GOVERNANCE, GOVERNANCE_SEGMENTS
)

logger = logging.getLogger(__name__)


def compute_quality_score(company):
    """
    Score 0-100 based on fundamental quality.
    Sub-components: ROIC, Revenue Growth, EBITDA Margin, Leverage.
    """
    scores = []

    # ROIC (0-25)
    roic = company.get("roic") or company.get("roe")
    if roic is not None:
        if roic > 0.25:
            s = 25
        elif roic > 0.15:
            s = 20
        elif roic > 0.10:
            s = 15
        elif roic > 0.05:
            s = 10
        elif roic > 0:
            s = 5
        else:
            s = 0
        scores.append(s)
    else:
        scores.append(10)  # neutral

    # Revenue Growth (0-25)
    growth = company.get("revenue_cagr_3y") or company.get("revenue_growth")
    if growth is not None:
        if growth > 0.20:
            s = 25
        elif growth > 0.10:
            s = 20
        elif growth > 0.05:
            s = 15
        elif growth > 0:
            s = 10
        elif growth > -0.05:
            s = 5
        else:
            s = 0
        scores.append(s)
    else:
        scores.append(10)

    # EBITDA Margin (0-25)
    margin = company.get("margin_ebitda") or company.get("operating_margins")
    if margin is not None:
        if margin > 0.40:
            s = 25
        elif margin > 0.25:
            s = 20
        elif margin > 0.15:
            s = 15
        elif margin > 0.08:
            s = 10
        elif margin > 0:
            s = 5
        else:
            s = 0
        scores.append(s)
    else:
        scores.append(10)

    # Leverage — Net Debt/EBITDA (0-25, lower is better)
    leverage = company.get("net_debt_ebitda")
    if leverage is not None:
        if leverage < 0:
            s = 25  # Net cash
        elif leverage < 1.0:
            s = 22
        elif leverage < 2.0:
            s = 18
        elif leverage < 3.0:
            s = 12
        elif leverage < 4.0:
            s = 6
        else:
            s = 0
        scores.append(s)
    else:
        scores.append(12)

    return round(sum(scores) / len(scores) * 4, 1)  # Scale to 0-100


def compute_valuation_score(valuation_result):
    """
    Score 0-100 based on valuation attractiveness.
    Sub-components: DCF upside, multiples discount, safety margin.
    """
    if not valuation_result or valuation_result.get("error"):
        return 50.0

    scores = []
    weights = []

    # DCF Upside (0-50)
    upside_dcf = None
    dcf = valuation_result.get("dcf")
    if dcf:
        upside_dcf = dcf.get("upside_dcf")
    if upside_dcf is not None:
        if upside_dcf > 0.50:
            s = 50
        elif upside_dcf > 0.30:
            s = 40
        elif upside_dcf > 0.15:
            s = 30
        elif upside_dcf > 0.05:
            s = 20
        elif upside_dcf > -0.10:
            s = 10
        else:
            s = 0
        scores.append(s)
        weights.append(0.50)

    # Multiples discount (0-30)
    mult = valuation_result.get("multiples")
    if mult:
        upside_mult = mult.get("upside_multiples")
        if upside_mult is not None:
            if upside_mult > 0.30:
                s = 30
            elif upside_mult > 0.15:
                s = 22
            elif upside_mult > 0:
                s = 15
            elif upside_mult > -0.15:
                s = 8
            else:
                s = 0
            scores.append(s)
            weights.append(0.30)

    # Overall upside as safety margin (0-20)
    upside = valuation_result.get("upside")
    if upside is not None:
        if upside > 0.40:
            s = 20
        elif upside > 0.20:
            s = 15
        elif upside > 0.05:
            s = 10
        elif upside > -0.10:
            s = 5
        else:
            s = 0
        scores.append(s)
        weights.append(0.20)

    if not scores:
        return 50.0

    total_w = sum(weights)
    raw = sum(s * w / total_w for s, w in zip(scores, weights))
    return round(min(100, max(0, raw * 2)), 1)  # Scale up


def compute_momentum_score(company):
    """
    Score 0-100 based on price momentum + liquidity.
    """
    scores = []

    # 3-month return vs market (0-40)
    ret_3m = company.get("ret_3m")
    if ret_3m is not None:
        if ret_3m > 0.15:
            s = 40
        elif ret_3m > 0.05:
            s = 30
        elif ret_3m > -0.05:
            s = 20
        elif ret_3m > -0.15:
            s = 10
        else:
            s = 0
        scores.append(s)
    else:
        scores.append(20)

    # 6-month return (0-30)
    ret_6m = company.get("ret_6m")
    if ret_6m is not None:
        if ret_6m > 0.20:
            s = 30
        elif ret_6m > 0.05:
            s = 22
        elif ret_6m > -0.05:
            s = 15
        elif ret_6m > -0.20:
            s = 8
        else:
            s = 0
        scores.append(s)
    else:
        scores.append(15)

    # Liquidity — avg volume 20d (0-30)
    vol = company.get("avg_volume_20d", 0) or 0
    if vol > 10_000_000:
        s = 30
    elif vol > 5_000_000:
        s = 25
    elif vol > 1_000_000:
        s = 20
    elif vol > 500_000:
        s = 15
    elif vol > 100_000:
        s = 10
    else:
        s = 5
    scores.append(s)

    return round(sum(scores), 1)


def compute_governance_score(ticker):
    """
    Score 0-100 based on corporate governance proxy.
    """
    segment = TICKER_GOVERNANCE.get(ticker, "tradicional")
    return float(GOVERNANCE_SEGMENTS.get(segment, 25))


def compute_composite_score(
    company, valuation_result, macro_global_score,
    macro_brazil_score, sector_score, is_fii=False, fii_score=None
):
    """
    Compute final composite score (0-100) with weighted components.
    
    Weights:
    - 30% Macro alignment
    - 25% Quality
    - 25% Valuation
    - 15% Momentum
    - 5% Governance
    """
    ticker = company.get("ticker", "")
    w = SCORE_WEIGHTS

    # Macro alignment: blend global + brazil + sector
    macro_score = (
        macro_global_score * 0.35 +
        macro_brazil_score * 0.35 +
        sector_score * 0.30
    )

    # Quality
    if is_fii and fii_score is not None:
        quality_score = fii_score
    else:
        quality_score = compute_quality_score(company)

    # Valuation
    val_score = compute_valuation_score(valuation_result)

    # Momentum
    momentum_score = compute_momentum_score(company)

    # Governance
    gov_score = compute_governance_score(ticker)

    # Weighted composite
    composite = (
        macro_score * w["macro"] +
        quality_score * w["quality"] +
        val_score * w["valuation"] +
        momentum_score * w["momentum"] +
        gov_score * w["governance"]
    )

    composite = round(min(100, max(0, composite)), 1)

    return {
        "score": composite,
        "macro_score": round(macro_score, 1),
        "quality_score": round(quality_score, 1),
        "valuation_score": round(val_score, 1),
        "momentum_score": round(momentum_score, 1),
        "governance_score": round(gov_score, 1),
    }


def classify_asset(score_data, valuation_result, macro_score):
    """
    Classify asset as Promissor, Neutro, or Viés Ruim.
    """
    score = score_data.get("score", 0)
    upside = valuation_result.get("upside") if valuation_result else None

    th = THRESHOLDS
    macro_positive = macro_score >= 50

    # Promissor: Score ≥ 75 + upside > 20% + macro positive
    if (score >= th["promissor_score"] and
        upside is not None and upside > th["promissor_upside"] and
        macro_positive):
        return "Promissor"

    # Viés Ruim: Score < 45 OR strong negative upside
    if score < th["ruim_score"]:
        return "Viés Ruim"
    if upside is not None and upside < th["ruim_upside"]:
        return "Viés Ruim"

    # Neutro: everything else
    return "Neutro"
