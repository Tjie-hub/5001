import sys; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np
with connect(read_only=True) as c:
    o=pd.read_sql("""SELECT ticker,date,close,volume FROM ohlcv
                     WHERE is_final=1 AND date>='2026-04-18' AND volume>0""",c)
o['val']=o.close*o.volume
adv=o.groupby('ticker').agg(adv=('val','mean'))
tk=adv[(adv.adv>=1e9)&(adv.adv<1e10)].index.tolist()
np.random.seed(5); tk=list(np.random.choice(tk,40,replace=False))
def tick(p): return 1 if p<200 else 2 if p<500 else 5 if p<2000 else 10 if p<5000 else 25
q=",".join("?"*len(tk))
with connect(read_only=True) as c:
    d=pd.read_sql(f"SELECT ticker,date,time,price,volume FROM ticks WHERE ticker IN ({q})",c,params=tk)
print(f"prints: {len(d):,}  tickers {d.ticker.nunique()}  days {d.date.nunique()}")
d['hm']=d.time.str[:5]
buckets={'open 09:00-09:05':('09:00','09:05'),'early 09:05-09:30':('09:05','09:30'),
         'mid 10:00-11:30':('10:00','11:30'),'pm 13:30-15:00':('13:30','15:00'),
         'close 15:45-16:15':('15:45','16:15')}
print("\n=== 18. AUCTION vs CONTINUOUS execution quality ===")
print(f"{'bucket':20} {'prints':>9} {'Roll %':>8} {'ret sd %':>9} {'vol share':>10}")
tot=d.volume.sum()
for lab,(a,b) in buckets.items():
    s=d[(d.hm>=a)&(d.hm<b)]
    rolls=[]
    for (t,dt),g in s.groupby(['ticker','date']):
        p=g.sort_values('time').price.values.astype(float)
        if len(p)<25: continue
        dp=np.diff(p); cv=np.cov(dp[1:],dp[:-1])[0,1]
        if cv<0: rolls.append(2*np.sqrt(-cv)/p.mean()*100)
    sd=s.groupby(['ticker','date']).price.apply(lambda x:x.pct_change().std()*100).median()
    print(f"{lab:20} {len(s):9,} {np.median(rolls) if rolls else float('nan'):8.3f} {sd:9.3f} "
          f"{100*s.volume.sum()/tot:9.1f}%")

print("\n=== opening print vs day VWAP (is the open a good fill?) ===")
vw=d.groupby(['ticker','date']).apply(lambda g:(g.price*g.volume).sum()/g.volume.sum())
op=d[d.hm<'09:05'].groupby(['ticker','date']).price.first()
cl=d[d.hm>='15:45'].groupby(['ticker','date']).price.last()
J=pd.DataFrame({'vwap':vw,'open':op,'close':cl}).dropna()
J['open_vs_vwap']=100*(J.open/J.vwap-1)
J['close_vs_vwap']=100*(J.close/J.vwap-1)
print(f"  n={len(J):,} ticker-days")
print(f"  open  vs VWAP: median {J.open_vs_vwap.median():+.3f}%  mean {J.open_vs_vwap.mean():+.3f}%  |sd| {J.open_vs_vwap.std():.3f}")
print(f"  close vs VWAP: median {J.close_vs_vwap.median():+.3f}%  mean {J.close_vs_vwap.mean():+.3f}%  |sd| {J.close_vs_vwap.std():.3f}")
print("  => a near-zero median means auction fills are not systematically worse than VWAP;")
print("     the dispersion (sd) is the execution risk you actually bear.")
