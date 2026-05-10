import yfinance as yf

for t in ['PETR4.SA','VALE3.SA','BBAS3.SA','VULC3.SA','ITUB4.SA','WEGE3.SA','ABEV3.SA','GRND3.SA']:
    info = yf.Ticker(t).info
    dy = info.get('dividendYield')
    dr = info.get('dividendRate')
    price = info.get('currentPrice') or info.get('regularMarketPrice')
    # If rate and price available, compute expected DY
    calc_dy = (dr / price * 100) if dr and price and price > 0 else None
    print(f"{t:10s}  DY_raw={str(dy):>8s}  Rate={str(dr):>8s}  Price={str(price):>8s}  Calc_DY%={calc_dy:.2f}%" if calc_dy else f"{t:10s}  DY_raw={str(dy):>8s}  Rate={str(dr):>8s}  Price={str(price):>8s}")
