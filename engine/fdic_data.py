"""
fdic_data.py — Integração com FDIC BankFind Suite API
Busca dados regulatórios reais de bancos americanos (para BDRs):
  - Tier 1 Capital Ratio (≈ CET1)
  - NPL Ratio (Non-Performing Loans)

API: https://banks.data.fdic.gov/api/
Dados: trimestrais. Cache local com TTL de 7 dias.
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_FDIC_BASE = "https://banks.data.fdic.gov/api/financials"
_CACHE_FILE = Path(__file__).parent.parent / "data" / "fdic_cache.json"
_CACHE_TTL_DAYS = 7
_TIMEOUT = 20

# ─── Mapeamento Ticker B3 → FDIC Certificate Number ──────────
FDIC_CERTS = {
    "JPMC34.SA": 628,     # JPMorgan Chase Bank, NA
    "MSBR34.SA": 32992,   # Morgan Stanley Bank, NA
}


def _load_cache():
    if _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(cache):
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"FDIC cache write error: {e}")


def _cache_valid(entry):
    if not entry or "fetched_at" not in entry:
        return False
    fetched = datetime.fromisoformat(entry["fetched_at"])
    return datetime.now() - fetched < timedelta(days=_CACHE_TTL_DAYS)


def _get_latest_report_date():
    """Return the FDIC report date in YYYYMMDD format for the latest available quarter."""
    now = datetime.now()
    # FDIC publishes ~45 days after quarter end
    ref = now - timedelta(days=60)
    month = ((ref.month - 1) // 3) * 3 + 3
    year = ref.year
    if month > 12:
        month = 12
    # Last day of quarter month
    last_day = {3: 31, 6: 30, 9: 30, 12: 31}[month]
    return f"{year}{month:02d}{last_day}"


def fetch_fdic_regulatory(ticker: str, use_cache: bool = True) -> dict:
    """
    Fetch real regulatory data for a US bank BDR from FDIC BankFind API.

    Returns dict with keys:
        cet1_real, npl_real, fonte_cet1, fonte_npl, fdic_reference_date
    or empty dict if ticker not mapped or API unavailable.
    """
    cert = FDIC_CERTS.get(ticker)
    if not cert:
        return {}

    cache = _load_cache()
    cache_key = ticker

    if use_cache and cache_key in cache and _cache_valid(cache[cache_key]):
        logger.debug(f"FDIC cache hit for {ticker}")
        return cache[cache_key]["data"]

    report_date = _get_latest_report_date()
    result = {}

    try:
        # Fields:
        #   RBCT1   = Tier 1 Capital Ratio (as percent, e.g. 13.5)
        #   DRNPASTM = NPL ratio (past due 90+ days and nonaccrual / total loans, %)
        #   REPDTE  = Report date (YYYYMMDD)
        params = {
            "filters": f"REPDTE%3A{report_date}%20AND%20CERT%3A{cert}",
            "fields": "CERT,REPDTE,IDT1CER",
            "limit": 1,
            "sort_by": "REPDTE",
            "sort_order": "DESC",
            "output": "json",
        }
        url = f"{_FDIC_BASE}?filters=REPDTE:{report_date}%20AND%20CERT:{cert}&fields=CERT,REPDTE,IDT1CER&limit=1&output=json"
        resp = requests.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json().get("data", [])

        if not data:
            # Try without specific date (get latest available)
            url2 = f"{_FDIC_BASE}?filters=CERT:{cert}&fields=CERT,REPDTE,IDT1CER&limit=1&sort_by=REPDTE&sort_order=DESC&output=json"
            resp2 = requests.get(url2, timeout=_TIMEOUT)
            resp2.raise_for_status()
            data = resp2.json().get("data", [])

        if data:
            row = data[0].get("data", data[0])
            ref_date = str(row.get("REPDTE", report_date))
            # Format date as YYYY-MM for display
            if len(ref_date) == 8:
                ref_display = f"{ref_date[:4]}-{ref_date[4:6]}"
            else:
                ref_display = ref_date

            # Tier 1 Capital Ratio → CET1 proxy (FDIC returns as percent)
            rbct1 = row.get("IDT1CER")
            if rbct1 is not None:
                result["cet1_real"] = round(float(rbct1) / 100.0, 4)
                result["fonte_cet1"] = "FDIC"
                result["fdic_reference_date"] = ref_display

            # NPL ratio
            drnpastm = row.get("DRNPASTM")
            if drnpastm is not None:
                result["npl_real"] = round(float(drnpastm) / 100.0, 4)
                result["fonte_npl"] = "FDIC"

    except Exception as e:
        logger.warning(f"FDIC query error for {ticker} (CERT={cert}): {e}")
        return {}

    if result:
        logger.info(f"FDIC real data fetched for {ticker}: {list(result.keys())}")
        cache[cache_key] = {
            "fetched_at": datetime.now().isoformat(),
            "data": result,
        }
        _save_cache(cache)

    return result
