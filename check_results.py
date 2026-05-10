import pandas as pd
df = pd.read_csv('data/analysis_results.csv')
print(f'Total: {len(df)} ativos')
prom = df[df["Rating"]=="Promissor"]
neut = df[df["Rating"]=="Neutro"]
ruim = df[df["Rating"]=="Vi\u00e9s Ruim"]
print(f'Promissores: {len(prom)}')
print(f'Neutros: {len(neut)}')
print(f'Vies Ruim: {len(ruim)}')
print()
print('Distribuicao de Upside:')
print(df['Upside'].describe())
print()
capped_pos = len(df[df['Upside']==0.50])
capped_neg = len(df[df['Upside']==-0.50])
mid = len(df[(df['Upside']>-0.30)&(df['Upside']<0.30)])
print(f'Upside == +50% (capped): {capped_pos}')
print(f'Upside == -50% (capped): {capped_neg}')
print(f'Upside entre -30% e +30%: {mid}')
print()
print('Top 10 por Score:')
for _, r in df.head(10).iterrows():
    u = r.get('Upside')
    t = r.get('Ticker','')
    s = r.get('Score',0)
    rt = r.get('Rating','')
    if pd.notna(u):
        print(f'  {t:8s} Score={s:.0f} Upside={u:.1%} Rating={rt}')
    else:
        print(f'  {t:8s} Score={s:.0f} Upside=N/A Rating={rt}')
