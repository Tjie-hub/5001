import sys; sys.path.insert(0,".")
"""Impact-cost study for the volatility-exclusion book, by ADV band.

Two independent estimators from daily OHLCV:
  Amihud ILLIQ   = mean(|r_t| / value_t)  -> linear impact per rupiah traded
  Corwin-Schultz = 2-day high/low effective spread estimator (negatives -> 0)
Neither needs intraday data, both are standard, and they fail differently --
if they disagree wildly the answer is "unknown", not an average.
"""
from data.db import connect
import pandas as pd, numpy as np
pd.set_option('display.width',220)

with connect(read_only=True) as c:
    df=pd.read_sql("SELECT ticker,date,open,high,low,close,volume FROM ohlcv WHERE is_final=1",c)
df['date']=pd.to_datetime(df.date); df=df.sort_values(['ticker','date']).reset_index(drop=True)
df=df[(df.volume>0)&(df.close>0)&(df.high>=df.low)&(df.low>0)]
df['val']=df.close*df.volume
g=df.groupby('ticker',group_keys=False)
df['adv60']=g.val.transform(lambda s:s.rolling(60,min_periods=60).mean())
df['ret']=g.close.transform(lambda s:s.pct_change())

# ---- Amihud ----
df['illiq']=(df.ret.abs()/df.val)          # return per rupiah

# ---- Corwin-Schultz (2-day) ----
hi2=np.maximum(df.high, g.high.transform(lambda s:s.shift(1)))
lo2=np.minimum(df.low,  g.low.transform(lambda s:s.shift(1)))
same=g.ticker.transform(lambda s:s.shift(1)).notna()
b=(np.log(df.high/df.low)**2)+(np.log(g.high.transform(lambda s:s.shift(1))/
                                      g.low.transform(lambda s:s.shift(1)))**2)
gam=np.log(hi2/lo2)**2
k=2-np.sqrt(2); den=3-2*np.sqrt(2)
a=(np.sqrt(2*b)-np.sqrt(b))/den - np.sqrt(gam/den)
cs=2*(np.exp(a)-1)/(1+np.exp(a))
df['cs']=np.where(same, np.clip(cs,0,None), np.nan)

d=df[df.adv60.notna()&(df.close>=50)].copy()
bands=[(1e9,2e9,'Rp 1-2bn'),(2e9,4e9,'Rp 2-4bn'),(4e9,1e10,'Rp 4-10bn'),
       (1e10,5e10,'Rp 10-50bn'),(5e10,np.inf,'Rp >50bn')]
print("=== LIQUIDITY BY ADV BAND (month-end snapshots, 2021-09 -> 2026-09) ===\n")
rows=[]
me=d.groupby(d.date.dt.to_period('M')).date.max()
snap=d[d.date.isin(me)]
for lo_,hi_,lab in bands:
    s=snap[(snap.adv60>=lo_)&(snap.adv60<hi_)]
    w=d[(d.adv60>=lo_)&(d.adv60<hi_)]
    rows.append((lab,len(s)/snap.date.nunique(),
                 w.cs.median()*100, w.cs.quantile(.75)*100,
                 w.illiq.median()*1e9*100,          # % move per Rp 1bn traded
                 w.ret.std()*100))
R=pd.DataFrame(rows,columns=['ADV band','avg names/mo','CS spread %','CS p75 %',
                             'Amihud %/Rp1bn','daily vol %'])
print(R.to_string(index=False,float_format=lambda x:f"{x:.3f}"))
