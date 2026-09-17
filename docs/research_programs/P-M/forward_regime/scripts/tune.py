import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',250)
d=pd.read_pickle(f"{SP}/ma.pkl"); g=d.groupby('ticker',sort=False)
d['sl']=g['slope'].shift(1); d['er']=g['ER'].shift(1); d['pa']=g['pct_above'].shift(1)
d=d[d.ticker!='IHSG']
ok=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)&d.f20.notna()&d.m20.notna()&(d.bad20.fillna(1)==0)).values
SL=d.sl.values; ER=d.er.values; PA=d.pa.values
EX=(d.f20.values-d.m20.values); DT=d.date.values; YR=pd.DatetimeIndex(d.date).year.values
IS=(YR<=2023); OOS=(YR>=2024)
rows=[]
for s,e,p in itertools.product([0.00,0.02,0.05,0.10],[0.20,0.30,0.40,0.50],[0.50,0.70,0.90]):
    m=ok&(SL>s)&(ER>=e)&(PA>=p)
    if m.sum()<300: continue
    r={'slope':s,'ER':e,'pa':p,'N':int(m.sum())}
    for nm,sub in [('FULL',m),('IS(21-23)',m&IS),('OOS(24-26)',m&OOS)]:
        if sub.sum()<100: r[nm]=np.nan; continue
        mu,t=cluster_t(EX[sub],DT[sub]); r[nm]=mu*100; r[nm+'_t']=t
    rows.append(r)
R=pd.DataFrame(rows)
base=R[(R.slope==0.02)&(R.ER==0.30)&(R.pa==0.70)].iloc[0]
print("=== 48-cell threshold grid, endpoint = 20d excess vs IHSG ===")
print("cells: %d | FULL excess: mean %.2f%%  min %.2f%%  max %.2f%%"%(len(R),R.FULL.mean(),R.FULL.min(),R.FULL.max()))
print("\nCHOSEN spec (slope .02 / ER .30 / pa .70): FULL %+.2f%%  IS %+.2f%%  OOS %+.2f%%"%(base.FULL,base['IS(21-23)'],base['OOS(24-26)']))
best_is=R.loc[R['IS(21-23)'].idxmax()]
best_full=R.loc[R.FULL.idxmax()]
print("\nBEST-on-IS  cell (slope %.2f/ER %.2f/pa %.2f): IS %+.2f%%  -> OOS %+.2f%%"%(
  best_is.slope,best_is.ER,best_is.pa,best_is['IS(21-23)'],best_is['OOS(24-26)']))
print("BEST-on-FULL cell (slope %.2f/ER %.2f/pa %.2f): FULL %+.2f%% (in-sample optimum)"%(
  best_full.slope,best_full.ER,best_full.pa,best_full.FULL))
print("\n  >>> tuning premium = BEST-on-IS OOS (%.2f%%) minus CHOSEN OOS (%.2f%%) = %+.2f%%"%(
  best_is['OOS(24-26)'],base['OOS(24-26)'],best_is['OOS(24-26)']-base['OOS(24-26)']))
print("\n=== how flat is the surface? OOS excess by cell, sorted on IS rank ===")
R['IS_rank']=R['IS(21-23)'].rank(ascending=False)
print(R.sort_values('IS_rank').head(8)[['slope','ER','pa','N','IS(21-23)','OOS(24-26)']].to_string(index=False,float_format=lambda x:f"{x:.2f}"))
print("\ncorrelation between IS rank and OOS performance: %.3f"%R[['IS(21-23)','OOS(24-26)']].corr().iloc[0,1])
