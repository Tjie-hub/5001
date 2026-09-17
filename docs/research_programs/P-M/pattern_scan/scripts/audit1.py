import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',270); COST=0.006
d=pd.read_pickle(f"{SP}/panel2.pkl").sort_values(['ticker','date']).reset_index(drop=True)
g=d.groupby('ticker',sort=False)
d['nz']=(d.volume>0).astype(int)
d['nz20']=g['nz'].transform(lambda s:s.shift(1).rolling(20,min_periods=20).sum())
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)&(d.volume>0)&(d.nz20>=18)).fillna(False).astype(bool)
d['hi20']=g['high'].transform(lambda s:s.rolling(20,min_periods=20).max()).groupby(d.ticker).shift(1)
d['lo20']=g['low'].transform(lambda s:s.rolling(20,min_periods=20).min()).groupby(d.ticker).shift(1)
d['nopen']=g['open'].shift(-1)                       # next session's open = realistic fill
# ---- EW universe benchmark (equal-weight liquid book), for comparison with IHSG ----
ew=d[d.liq].groupby('date')['ret'].mean()
ewi=(1+ew.fillna(0)).cumprod()
for h in [5,20]:
    f=(ewi.shift(-h)/ewi-1).rename(f'ew{h}')
    d=d.merge(f.reset_index(),on='date',how='left')
g=d.groupby('ticker',sort=False)
# forward return measured FROM NEXT OPEN to close h days after the signal
for h in [5,20]:
    d[f'fo{h}']=g['close'].shift(-h)/d['nopen']-1
pats={
 'failed breakdown':(d.low<d.lo20)&(d.close>d.lo20),
 'resistance breakout':(d.close>d.hi20),
 'failed breakout':(d.high>d.hi20)&(d.close<d.hi20),
}
rows=[]
for nm,m in pats.items():
    m=(m&d.liq).fillna(False)
    for h in [5,20]:
        s=d[m&d[f'f{h}'].notna()&d[f'fo{h}'].notna()&d[f'm{h}'].notna()&d[f'ew{h}'].notna()&(d[f'bad{h}'].fillna(1)==0)]
        if len(s)<200: continue
        a,_=cluster_t((s[f'f{h}']-COST-s[f'm{h}']).values,s.date.values)          # close entry, IHSG bench
        b,tb=cluster_t((s[f'fo{h}']-COST-s[f'm{h}']).values,s.date.values)        # NEXT-OPEN entry, IHSG
        c,tc=cluster_t((s[f'fo{h}']-COST-s[f'ew{h}']).values,s.date.values)       # NEXT-OPEN entry, EW bench
        rows.append((nm,h,len(s),a*100,b*100,tb,c*100,tc))
print("=== AUDIT: entry realism + benchmark choice ===")
print(pd.DataFrame(rows,columns=['pattern','h','N','close-entry vs IHSG%','NEXT-OPEN vs IHSG%','t','NEXT-OPEN vs EW-universe%','t']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
print()
s=d[d.liq&d.f20.notna()&d.m20.notna()&d.ew20.notna()]
mu,t=cluster_t((s.f20-s.m20).values,s.date.values); print("unconditional liquid stock vs IHSG   , 20d: %+.2f%% (t %.2f)"%(100*mu,t))
mu,t=cluster_t((s.f20-s.ew20).values,s.date.values); print("unconditional liquid stock vs EW-book, 20d: %+.2f%% (t %.2f)  <- a fair benchmark nets to ~0"%(100*mu,t))
