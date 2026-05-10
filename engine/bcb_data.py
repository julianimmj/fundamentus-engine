"""
bcb_data.py — Integração com BCB OLINDA API
Busca dados regulatórios reais do Banco Central do Brasil:
  - CET1 / Índice de Basileia Nível 1
  - NPL (Inadimplência > 90 dias)
  - NIM (Margem Líquida de Juros)
  - Cost/Income (Eficiência Administrativa)

Dados: trimestrais, ~45 dias de atraso após fechamento.
Cache local em JSON com TTL de 7 dias.
"""
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# ─── Base URL BCB OLINDA ───────────────────────────────────────
_BCB_BASE = (
    "https://olinda.bcb.gov.br/olinda/servico/IF_Data/versao/v1/odata"
)
_CACHE_FILE = Path(__file__).parent.parent / "data" / "bcb_cache.json"
_CACHE_TTL_DAYS = 7
_TIMEOUT = 20

# ─── Mapeamento Ticker → Código BCB (CNPJ Raiz) ───────────────
BCB_CODES = {
    "ITUB4.SA":  "60701190",   # Itaú Unibanco Holding
    "ITSA4.SA":  "60701190",   # Holding Itaú → usa dados do banco
    "BBDC4.SA":  "60746948",   # Bradesco
    "BBDC3.SA":  "60746948",
    "BBAS3.SA":  "00000000",   # Banco do Brasil (código BCB especial = 1)
    "SANB11.SA": "90400888",   # Santander Brasil
    "BPAC11.SA": "30306294",   # BTG Pactual
    "BRSR6.SA":  "92702067",   # Banrisul
    "ABCB4.SA":  "28195667",   # ABC Brasil
    "PINE4.SA":  "62144175",   # Pine
    "BMGB4.SA":  "61186680",   # BMG
    "BRBI11.SA": "13059145",   # BR Investimentos
}

# Código BCB numérico para o Banco do Brasil
_BB_BCB_CODE = 1


def _load_cache():
    """Load cache from disk."""
    if _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(cache):
    """Save cache to disk."""
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"BCB cache write error: {e}")


def _cache_valid(entry):
    """Check if a cache entry is still valid (within TTL)."""
    if not entry or "fetched_at" not in entry:
        return False
    fetched = datetime.fromisoformat(entry["fetched_at"])
    return datetime.now() - fetched < timedelta(days=_CACHE_TTL_DAYS)


def _get_latest_quarter():
    """Return the latest available quarter string (YYYY-MM)."""
    now = datetime.now()
    # BCB publishes with ~45 day lag; subtract 2 months to be safe
    ref = now - timedelta(days=60)
    # Snap to last quarter end
    month = ((ref.month - 1) // 3) * 3 + 3  # 3, 6, 9, or 12
    year = ref.year
    if month > 12:
        month = 12
    return f"{year}-{month:02d}"


def _query_bcb(endpoint, cnpj_raiz, quarter):
    """
    Query a BCB IF.data endpoint for a given institution and quarter.
    Returns the first result dict or None.
    """
    # For Banco do Brasil the CNPJ code is "1" (special case)
    code = _BB_BCB_CODE if cnpj_raiz == "00000000" else int(cnpj_raiz)

    url = (
        f"{_BCB_BASE}/{endpoint}"
        f"(Data=@Data,CodigoInstituicao=@Cod)"
        f"?@Data='{quarter}'"
        f"&@Cod={code}"
        f"&$format=json"
        f"&$select=Valor,Data,NomeInstituicao"
    )
    try:
        resp = requests.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json().get("value", [])
        return data[0] if data else None
    except Exception as e:
        logger.debug(f"BCB query error [{endpoint}] CNPJ={cnpj_raiz}: {e}")
        return None


def fetch_bcb_regulatory(ticker: str, use_cache: bool = True) -> dict:
    """
    Fetch real regulatory data for a Brazilian bank from BCB OLINDA API.

    Returns dict with keys:
        cet1_real, npl_real, nim_real, cost_income_real,
        fonte_cet1, fonte_npl, bcb_reference_date
    or empty dict if ticker not mapped or API unavailable.
    """
    cnpj = BCB_CODES.get(ticker)
    if not cnpj:
        return {}

    cache = _load_cache()
    cache_key = ticker

    if use_cache and cache_key in cache and _cache_valid(cache[cache_key]):
        logger.debug(f"BCB cache hit for {ticker}")
        return cache[cache_key]["data"]

    quarter = _get_latest_quarter()
    result = {}

    # ── CET1 / Índice de Basileia Nível 1 ──────────────────────
    # Endpoint: IndicedeBasileia → campo "Valor" = Basileia total (≈ CET1 + Tier2)
    # Nível 1 proxy: typically ~85-90% of total Basel. Use as CET1 proxy.
    # Better endpoint would be "IndicedeNivel1" but fallback to IndicedeBasileia
    cet1_resp = _query_bcb("IndicedeNivel1", cnpj, quarter)
    if cet1_resp and cet1_resp.get("Valor") is not None:
        val = float(cet1_resp["Valor"]) / 100.0  # BCB returns in percent (e.g. 13.5)
        result["cet1_real"] = round(val, 4)
        result["fonte_cet1"] = "BCB"
        result["bcb_reference_date"] = quarter
    else:
        # Try full Basel index as fallback
        bas_resp = _query_bcb("IndicedeBasileia", cnpj, quarter)
        if bas_resp and bas_resp.get("Valor") is not None:
            val = float(bas_resp["Valor"]) / 100.0 * 0.88  # ~88% is Tier 1 historically
            result["cet1_real"] = round(val, 4)
            result["fonte_cet1"] = "BCB (Basileia)"
            result["bcb_reference_date"] = quarter

    # ── NPL (Inadimplência > 90 dias) ─────────────────────────
    npl_resp = _query_bcb("IndicedeInadimplencia", cnpj, quarter)
    if npl_resp and npl_resp.get("Valor") is not None:
        val = float(npl_resp["Valor"]) / 100.0
        result["npl_real"] = round(val, 4)
        result["fonte_npl"] = "BCB"
    
    # ── NIM (Margem Líquida de Juros) ─────────────────────────
    nim_resp = _query_bcb("MargemLiquidaDeJuros", cnpj, quarter)
    if nim_resp and nim_resp.get("Valor") is not None:
        val = float(nim_resp["Valor"]) / 100.0
        result["nim_real"] = round(val, 4)

    # ── Cost/Income (Eficiência Administrativa) ────────────────
    eff_resp = _query_bcb("EficienciaAdministrativa", cnpj, quarter)
    if eff_resp and eff_resp.get("Valor") is not None:
        val = float(eff_resp["Valor"]) / 100.0
        result["cost_income_real"] = round(val, 4)

    if result:
        logger.info(f"BCB real data fetched for {ticker}: {list(result.keys())}")
        # Cache the result
        cache[cache_key] = {
            "fetched_at": datetime.now().isoformat(),
            "data": result,
        }
        _save_cache(cache)

    return result
