import pandas as pd
df = pd.read_csv('data/analysis_results.csv')
dy = df[['Ticker','Div. Yield']].dropna().sort_values('Div. Yield', ascending=False)
print('Top 15 DY (valores corrigidos):')
for _, r in dy.head(15).iterrows():
    v = r['Div. Yield']
    print(f"  {r['Ticker']:8s}  raw={v:.4f}  display={v*100:.1f}%")
print()
print(f"Mediana DY: {dy['Div. Yield'].median()*100:.1f}%")
print(f"Media DY: {dy['Div. Yield'].mean()*100:.1f}%")
