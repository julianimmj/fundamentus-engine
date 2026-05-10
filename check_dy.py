import yfinance as yf

# Test a mix of stocks, BDRs, and FIIs
tickers = ['PETR4.SA','VALE3.SA','WEGE3.SA','BBAS3.SA','ITUB4.SA','VULC3.SA','GRND3.SA',
           'AAPL34.SA','MSFT34.SA','HGLG11.SA','MXRF11.SA','VGIR11.SA']

print(f"{'Ticker':10s} {'Rate':>8s} {'Price':>8s} {'DY_raw':>8s} {'DY_calc':>8s} {'DY_final':>8s}")
print("-" * 62)

for t in tickers:
    info = yf.Ticker(t).info
    rate = info.get('dividendRate')
    price = info.get('currentPrice') or info.get('regularMarketPrice')
    dy_raw = info.get('dividendYield')
    
    # Compute as our engine would
    if rate and price and price > 0 and rate > 0:
        dy_final = rate / price
        if dy_final >= 0.60:
            dy_final = None
    else:
        dy_final = dy_raw
        if dy_final and abs(dy_final) > 1.0:
            dy_final = dy_final / 100.0
        if dy_final and not (0 < dy_final < 0.60):
            dy_final = None

    rate_s = f"{rate}" if rate else "N/A"
    price_s = f"{price}" if price else "N/A"
    raw_s = f"{dy_raw}" if dy_raw else "N/A"
    calc_s = f"{dy_final:.4f}" if dy_final else "N/A"
    disp_s = f"{dy_final*100:.1f}%" if dy_final else "N/A"
    
    print(f"{t:10s} {rate_s:>8s} {price_s:>8s} {raw_s:>8s} {calc_s:>8s} {disp_s:>8s}")
