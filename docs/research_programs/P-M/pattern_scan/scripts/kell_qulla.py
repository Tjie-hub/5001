import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',260); COST=0.006
d=pd.read_pickle(f"{SP}/panel2.pkl").sort_values(['ticker','date']).reset_index(drop=True)
g=d.groupby('ticker',sort=False)
d['ema10']=g['close'].transform(lambda s:s.ewm(span=10,adjust=False,min_periods=10).mean())
d['ema20']=g['close'].transform(lambda s:s.ewm(span=20,adjust=False,min_periods=20).mean())
d['sma10']=g['close'].transform(lambda s:s.rolling(10,min_periods=10).mean())
d['v20']=g['volume'].transform(lambda s:s.rolling(20,min_periods=15).mean()).groupby(d.ticker).shift(1)
d['pc']=g['close'].shift(1)
d['nz']=(d.volume>0).astype(int)
d['nz20']=g['nz'].transform(lambda s:s.shift(1).rolling(20,min_periods=20).sum())
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)&(d.volume>0)&(d.nz20>=18)).fillna(False).astype(bool)
def slope(s,w=20):
    x=np.arange(w); xm=x.mean(); den=((x-xm)**2).sum()
    return s.rolling(w,min_periods=w).apply(lambda y:((x-xm)*(y-y.mean())).sum()/den,raw=True)
d['sh']=g['high'].transform(lambda s:slope(s))/d.close
d['slo']=g['low'].transform(lambda s:slope(s))/d.close
d['e20s']=d.ema20/g['ema20'].shift(10)-1
d['rng20']=((g['high'].transform(lambda s:s.rolling(20,min_periods=20).max())
            -g['low'].transform(lambda s:s.rolling(20,min_periods=20).min()))/d.close)
d['rng40']=((g['high'].transform(lambda s:s.rolling(40,min_periods=40).max())
            -g['low'].transform(lambda s:s.rolling(40,min_periods=40).min()))/d.close)
for c in ['sh','slo','e20s','rng20','rng40']: d[c+'_1']=g[c].shift(1)
d['ema10_1']=g['ema10'].shift(1); d['c1']=g['close'].shift(1); d['ema20_1']=g['ema20'].shift(1)

# ---- S1 WEDGE POP (Kell) ----
correction=(d.c1<d.ema20_1)&(d.e20s_1<0)                       # prior downtrend/correction
wedge=(d.sh_1<0)&(d.slo_1<0)&(d.sh_1<d.slo_1)&(d.rng20_1<0.8*d.rng40_1)   # converging, contracting
pop=(d.close>d.ema10)&(d.c1<=d.ema10_1)&(d.volume>1.2*d.v20)   # close back above 10EMA on above-avg vol
S1=d.liq&correction&wedge&pop
# ---- S2 EPISODIC PIVOT (Qullamaggie) ----
gap=(d.open/d.pc-1)
S2=d.liq&(gap>=0.05)&(gap<=0.25)&(d.volume>=3*d.v20)
# ARA check: did the gap day close at its high (limit-up, likely unfillable)?
d['ara']=((d.close>=d.high*0.999)&(d.close/d.pc-1>=0.19)).astype(int)
print("S1 wedge-pop signals: %d | S2 episodic-pivot signals: %d"%(int(S1.sum()),int(S2.sum())))
print("S2 signals closing at/near limit-up (likely UNFILLABLE next day): %d (%.1f%%)"%(
    int(d[S2].ara.sum()),100*d[S2].ara.mean()))
def rep(nm,m):
    out=[nm,int(m.sum()),int(d[m].ticker.nunique())]
    for h in [5,10,20]:
        s=d[m&d[f'f{h}'].notna()&d[f'm{h}'].notna()&(d[f'bad{h}'].fillna(1)==0)]
        if len(s)<60: out+=[np.nan,np.nan]; continue
        mu,t=cluster_t((s[f'f{h}']-COST-s[f'm{h}']).values,s.date.values); out+=[mu*100,t]
    s=d[m&d.f20.notna()&d.m20.notna()&(d.bad20.fillna(1)==0)]
    s=s[pd.DatetimeIndex(s.date).year!=2025]
    if len(s)<60: out+=[np.nan,np.nan]
    else:
        mu,t=cluster_t((s.f20-COST-s.m20).values,s.date.values); out+=[mu*100,t]
    return out
rows=[rep('S1 Wedge Pop (Kell, faithful)',S1),
      rep('S2 Episodic Pivot (Qulla, daily proxy)',S2),
      rep('S2b EP excluding limit-up closes',S2&(d.ara==0))]
print()
print(pd.DataFrame(rows,columns=['strategy','N','tickers','exc5%','t','exc10%','t','exc20%','t','exc20 ex25%','t']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
d[S1].to_pickle(f"{SP}/s1.pkl"); d[S2].to_pickle(f"{SP}/s2.pkl")
