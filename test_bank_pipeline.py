import logging
from engine.runner import run_full_analysis
import pandas as pd

logging.basicConfig(level=logging.INFO)

# Run only for a few banks and a normal stock to test the pipeline
tickers_to_test = ["ITUB4.SA", "BBAS3.SA", "PETR4.SA", "BBDC4.SA"]

print(f"Running analysis for: {tickers_to_test}")
result = run_full_analysis(tickers=tickers_to_test, max_workers=2, use_cache=False)

df = result["results"]

print("\n--- RESULTS ---")
columns_to_show = ["Ticker", "Tipo", "Rating", "Score", "Target Price", "Upside", "Método Val."]
bank_columns = ["NIM", "Cost/Income", "CET1 Proxy", "NPL Proxy", "Cresc. Carteira", "PDD/Lucro"]

for col in columns_to_show + bank_columns:
    if col not in df.columns:
        df[col] = None

print(df[columns_to_show + bank_columns].to_string())
