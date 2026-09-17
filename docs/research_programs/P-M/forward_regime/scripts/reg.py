import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',260)
d=pd.read_pickle(f"{SP}/ma.pkl"); g=d.groupby('ticker',sort=False)
liq=(d.adv20>=1e9)&(d.close>=50)&(d.n>=25)
sl=g['slope'].shift(1); er=g['ER'].shift(1); pa=g['pct_above'].shift(1); cr=g['cross'].shift(1)
UP=(sl>0.02)&(er>=0.30)&(pa>=0.70); SIDE=(sl.abs()<0.01)&(er<0.20)&(cr>=4)
print("=== REGIME effect (all days in regime, no touch required), excess vs IHSG ===")
out=[]
for rn,R in [('UPTREND',UP),('SIDEWAYS',SIDE)]:
    for h in [5,10,20]:
        s=d[liq&R&d[f'f{h}'].notna()&d[f'm{h}'].notna()&(d[f'bad{h}'].fillna(1)==0)]
        mu,t=cluster_t(s[f'f{h}'].values-s[f'm{h}'].values,s.date.values)
        out.append((rn,h,len(s),mu*100,t))
print(pd.DataFrame(out,columns=['regime','h','N','exc%','t']).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
print("\n=== UPTREND h=5 excess, BY YEAR (is it another 2025 artifact?) ===")
s=d[liq&UP&d.f5.notna()&d.m5.notna()&(d.bad5.fillna(1)==0)].copy(); s['yr']=s.date.dt.year
o=[]
for y,gg in s.groupby('yr'):
    mu,t=cluster_t(gg.f5.values-gg.m5.values,gg.date.values); o.append((y,len(gg),mu*100,t))
print(pd.DataFrame(o,columns=['yr','N','exc%','t']).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
