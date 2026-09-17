import os,sys; sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'.')
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',260)
COST=0.006
d=pd.read_pickle(f"{SP}/panel2.pkl").sort_values(['ticker','date']).reset_index(drop=True)
g=d.groupby('ticker',sort=False)
d['nz']=(d.volume>0).astype(int)
d['nz20']=g['nz'].transform(lambda s:s.shift(1).rolling(20,min_periods=20).sum())
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)&(d.volume>0)&(d.nz20>=18)).fillna(False).astype(bool)
# rolling levels (shifted: known at t)
d['hi20']=g['high'].transform(lambda s:s.rolling(20,min_periods=20).max()).groupby(d.ticker).shift(1)
d['lo20']=g['low'].transform(lambda s:s.rolling(20,min_periods=20).min()).groupby(d.ticker).shift(1)
d['rng20']=(d.hi20-d.lo20)/d.close
d['rng40']=((g['high'].transform(lambda s:s.rolling(40,min_periods=40).max())
            -g['low'].transform(lambda s:s.rolling(40,min_periods=40).min()))/d.close).groupby(d.ticker).shift(1)
# slopes of highs / lows over 20 bars (converging-wedge test)
def slope(s,w=20):
    x=np.arange(w); xm=x.mean(); den=((x-xm)**2).sum()
    return s.rolling(w,min_periods=w).apply(lambda y:((x-xm)*(y-y.mean())).sum()/den,raw=True)
d['sh']=g['high'].transform(lambda s:slope(s))/d.close
d['slo']=g['low'].transform(lambda s:slope(s))/d.close
d['sh']=g['sh'].shift(1); d['slo']=g['slo'].shift(1)
ok=d.liq&d.f5.notna()&d.m5.notna()

# --- pattern definitions (all LONG, entry at close of signal bar) ---
pats={}
# 2. resistance breakout: close above prior 20d high
pats['P2 resistance breakout (close>20d high)'] = ok&(d.close>d.hi20)
# 3a. failed breakdown: broke below 20d low intraday, closed back above it
pats['P3a failed breakdown (sweep low, close back in)'] = ok&(d.low<d.lo20)&(d.close>d.lo20)
# 3b. failed breakout FADE-avoidance: broke above 20d high intraday but closed back below
pats['P3b failed breakout (poked high, closed below)'] = ok&(d.high>d.hi20)&(d.close<d.hi20)
# 4. falling wedge: highs and lows both falling, converging, range contracting, then close>prior high
conv=(d.sh<0)&(d.slo<0)&(d.sh<d.slo)&(d.rng20<0.8*d.rng40)
pats['P4 falling wedge + upside break'] = ok&conv&(d.close>g['high'].shift(1))
pats['P4b falling wedge (no break required)'] = ok&conv
def rep(nm,m):
    out=[nm,int(m.sum()),int(d[m].ticker.nunique())]
    for h in [5,10,20]:
        s=d[m&d[f'f{h}'].notna()&d[f'm{h}'].notna()&(d[f'bad{h}'].fillna(1)==0)]
        if len(s)<100: out+=[np.nan,np.nan]; continue
        exc=(s[f'f{h}']-COST-s[f'm{h}']).values
        mu,t=cluster_t(exc,s.date.values); out+=[mu*100,t]
    s=d[m&d.f20.notna()&d.m20.notna()&(d.bad20.fillna(1)==0)]
    s=s[pd.DatetimeIndex(s.date).year!=2025]
    mu,t=cluster_t((s.f20-COST-s.m20).values,s.date.values); out+=[mu*100,t]
    return out
rows=[rep(k,v) for k,v in pats.items()]
print("ALL LONG, entry at signal close, net 0.60% RT, excess vs IHSG, date-clustered SE")
print(pd.DataFrame(rows,columns=['pattern','N','tickers','exc5%','t','exc10%','t','exc20%','t','exc20 ex25%','t']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
