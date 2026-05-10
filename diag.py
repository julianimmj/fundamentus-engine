"""Diagnostic script to understand upside clamping issue."""
from engine.cache import get_cache
get_cache().clear()

from engine.runner import run_full_analysis
from engine.company_analysis import fetch_company_data
from engine.valuation import compute_wacc, compute_dcf, compute_multiples_valuation, compute_final_target
from engine.macro_global import fetch_global_macro
from engine.macro_brazil import fetch_brazil_macro

# Fetch macro first
mg = fetch_global_macro(use_cache=False)
mb = fetch_brazil_macro(use_cache=False)
print(f"Macro Global Score: {mg.get('score')}")
print(f"Macro Brasil Score: {mb.get('score')}")
print()

# Detailed analysis of specific tickers
for ticker in ['PETR4.SA', 'VALE3.SA', 'WEGE3.SA', 'ITUB4.SA']:
    c = fetch_company_data(ticker, use_cache=False)
    if c.get('error'):
        print(f"{ticker}: ERROR - {c['error']}")
        continue
    
    wacc = compute_wacc(c, mg, mb)
    dcf = compute_dcf(c, wacc)
    mult = compute_multiples_valuation(c, {})
    final = compute_final_target(c, dcf, mult)
    
    print(f"=== {ticker} ===")
    print(f"  Price: {c.get('current_price')}")
    print(f"  Revenue: {c.get('revenue_latest')}")
    print(f"  EBITDA: {c.get('ebitda_latest')}")
    print(f"  Net Income: {c.get('net_income_latest')}")
    print(f"  Net Debt: {c.get('net_debt')}")
    print(f"  Shares: {c.get('shares_outstanding')}")
    print(f"  Market Cap: {c.get('market_cap')}")
    print(f"  WACC: {wacc}")
    proj = c.get('projections', {})
    print(f"  Projections FCF: {proj.get('fcff', [])}")
    print(f"  Growth rates: {proj.get('growth_rates', [])}")
    if dcf:
        print(f"  DCF EV: {dcf.get('enterprise_value')}")
        print(f"  DCF Equity: {dcf.get('equity_value')}")
        print(f"  DCF Target: {dcf.get('target_price_dcf')}")
        print(f"  DCF Upside: {dcf.get('upside_dcf')}")
    else:
        print(f"  DCF: None")
    if mult:
        print(f"  Mult Target: {mult.get('target_price_multiples')}")
        print(f"  Mult Upside: {mult.get('upside_multiples')}")
    else:
        print(f"  Multiples: None")
    print(f"  FINAL Target: {final.get('target_price')}")
    print(f"  FINAL Upside: {final.get('upside')}")
    print()
