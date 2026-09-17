import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',270)
R=pd.read_pickle(f"{SP}/trades.pkl"); R=R[R.mkt.notna()].copy()
R['yr']=pd.to_datetime(R.date).dt.year
print("=== excess % by YEAR, per exit rule ===")
piv=[]
for r in ['hold20','flip','ema','atr3','ema_or_stop','stop8']:
    row={'rule':r}
    for y,gg in R[R.rule==r].groupby('yr'):
        mu,t=cluster_t(gg.net.values-gg.mkt.values,gg.date.values)
        row[y]=mu*100
    s=R[R.rule==r]; mu,t=cluster_t(s.net.values-s.mkt.values,s.date.values)
    row['ALL']=mu*100; row['t']=t
    piv.append(row)
print(pd.DataFrame(piv).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
print("\n=== years positive (out of 6) ===")
P=pd.DataFrame(piv).set_index('rule')[[2021,2022,2023,2024,2025,2026]]
print((P>0).sum(axis=1).to_string())
print("\n=== SMMT April 2026 episode: what each exit would have done ===")
s=R[(R.ticker=='SMMT')&(R.date>=pd.Timestamp('2026-04-01'))&(R.date<=pd.Timestamp('2026-05-01'))]
print(s[['date','rule','net','days','mae']].to_string(index=False,float_format=lambda x:f"{x:.3f}"))
