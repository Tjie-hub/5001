import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',270); COST=0.006
d=pd.read_pickle(f"{SP}/panel2.pkl").sort_values(['ticker','date']).reset_index(drop=True)
RG=pd.read_pickle(f"{SP}/ihsg_regime.pkl"); rgm=dict(zip(RG.date,RG.regime))
g=d.groupby('ticker',sort=False)
d['ema10']=g['close'].transform(lambda s:s.ewm(span=10,adjust=False,min_periods=10).mean())
d['ema20_']=g['close'].transform(lambda s:s.ewm(span=20,adjust=False,min_periods=20).mean())
d['v20']=g['volume'].transform(lambda s:s.rolling(20,min_periods=15).mean()).groupby(d.ticker).shift(1)
d['nz']=(d.volume>0).astype(int); d['nz20']=g['nz'].transform(lambda s:s.shift(1).rolling(20,min_periods=20).sum())
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)&(d.volume>0)&(d.nz20>=18)).fillna(False).astype(bool)
d['hi20']=g['high'].transform(lambda s:s.rolling(20,min_periods=20).max()).groupby(d.ticker).shift(1)
d['lo20']=g['low'].transform(lambda s:s.rolling(20,min_periods=20).min()).groupby(d.ticker).shift(1)
d['pc']=g['close'].shift(1); d['nopen']=g['open'].shift(-1)
d['fo20']=g['close'].shift(-20)/d['nopen']-1        # executable: next-open entry
def slope(s,w=20):
    x=np.arange(w); xm=x.mean(); den=((x-xm)**2).sum()
    return s.rolling(w,min_periods=w).apply(lambda y:((x-xm)*(y-y.mean())).sum()/den,raw=True)
d['sh']=(g['high'].transform(lambda s:slope(s))/d.close).groupby(d.ticker).shift(1)
d['slo']=(g['low'].transform(lambda s:slope(s))/d.close).groupby(d.ticker).shift(1)
d['rng20']=((g['high'].transform(lambda s:s.rolling(20,min_periods=20).max())-g['low'].transform(lambda s:s.rolling(20,min_periods=20).min()))/d.close).groupby(d.ticker).shift(1)
d['rng40']=((g['high'].transform(lambda s:s.rolling(40,min_periods=40).max())-g['low'].transform(lambda s:s.rolling(40,min_periods=40).min()))/d.close).groupby(d.ticker).shift(1)
d['e20s']=(d.ema20_/g['ema20_'].shift(10)-1).groupby(d.ticker).shift(1)
d['c1']=g['close'].shift(1); d['ema10_1']=g['ema10'].shift(1); d['ema20_1']=g['ema20_'].shift(1)
d['er']=g['ER'].shift(1) if 'ER' in d else np.nan
d['rg']=d.date.map(rgm)
ma=pd.read_pickle(f"{SP}/ma.pkl")[['ticker','date','slope','ER','pct_above']]
d=d.merge(ma,on=['ticker','date'],how='left')
gg=d.groupby('ticker',sort=False)
d['sl_1']=gg['slope'].shift(1); d['er_1']=gg['ER'].shift(1); d['pa_1']=gg['pct_above'].shift(1)
P={
 'TREND REGIME (spec 002 entry)':(d.sl_1>0.02)&(d.er_1>=0.30)&(d.pa_1>=0.70),
 'Resistance breakout':(d.close>d.hi20),
 'Episodic Pivot (gap>=5%, 3x vol)':((d.open/d.pc-1>=0.05)&(d.open/d.pc-1<=0.25)&(d.volume>=3*d.v20)),
 'Failed breakout (bull trap)':(d.high>d.hi20)&(d.close<d.hi20),
 'Failed breakdown (sweep 20d low)':(d.low<d.lo20)&(d.close>d.lo20),
 'Falling wedge + break':(d.sh<0)&(d.slo<0)&(d.sh<d.slo)&(d.rng20<0.8*d.rng40)&(d.close>gg['high'].shift(1)),
 'Wedge Pop (Kell)':((d.c1<d.ema20_1)&(d.e20s<0)&(d.sh<0)&(d.slo<0)&(d.sh<d.slo)&(d.rng20<0.8*d.rng40)
                     &(d.close>d.ema10)&(d.c1<=d.ema10_1)&(d.volume>1.2*d.v20)),
}
rows=[]
for nm,m in P.items():
    m=(m&d.liq&(d.rg=='BULL')).fillna(False)
    s=d[m&d.fo20.notna()&d.m20.notna()&(d.bad20.fillna(1)==0)]
    if len(s)<30: rows.append((nm,len(s),0,np.nan,np.nan,np.nan,np.nan)); continue
    net=(s.fo20-COST)*100; exc=net-s.m20*100
    mu,t=cluster_t((s.fo20-COST-s.m20).values,s.date.values)
    rows.append((nm,len(s),s.date.dt.to_period('M').nunique(),net.mean(),mu*100,t,100*(net>0).mean()))
R=pd.DataFrame(rows,columns=['strategy','trades','distinct months','ABS net20%','excess20%','t','win%'])
print("=== IHSG BULL regime only — next-open entry, 20d hold, net 0.60% ===")
print(R.sort_values('ABS net20%',ascending=False).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
print("\nBULL sample: 9 independent episodes, 98 sessions total.")

# ---- the missing control: what does a RANDOM liquid stock do in BULL? ----
b=d[d.liq&(d.rg=='BULL')&d.fo20.notna()&d.m20.notna()&(d.bad20.fillna(1)==0)]
base_net=((b.fo20-COST)*100).mean()
mu,t=cluster_t((b.fo20-COST-b.m20).values,b.date.values)
print()
print("=== CONTROL: every liquid ticker-day in BULL (no pattern at all) ===")
print("  N=%d  ABS net20 = %+.2f%%   excess = %+.2f%% (t %.2f)  win %.1f%%"%(
    len(b),base_net,mu*100,t,100*((b.fo20-COST)>0).mean()))
print()
print("=== RANK BY WHAT THE PATTERN ADDS OVER SIMPLY BEING LONG IN BULL ===")
rows=[]
for nm,m in P.items():
    m=(m&d.liq&(d.rg=='BULL')).fillna(False)
    s=d[m&d.fo20.notna()&d.m20.notna()&(d.bad20.fillna(1)==0)]
    if len(s)<30: continue
    net=((s.fo20-COST)*100).mean()
    # difference-in-means vs the BULL control, clustered on date
    x=np.r_[(s.fo20-COST).values,(b.fo20-COST).values]
    g_=np.r_[np.ones(len(s)),np.zeros(len(b))]; dt=np.r_[s.date.values,b.date.values]
    X=np.c_[np.ones(len(x)),g_]; beta=np.linalg.lstsq(X,x,rcond=None)[0]; e=x-X@beta
    XtXi=np.linalg.inv(X.T@X); meat=np.zeros((2,2))
    for k in pd.unique(dt):
        mm=dt==k; xs=X[mm]; es=e[mm]; sc=xs.T@es; meat+=np.outer(sc,sc)
    V=XtXi@meat@XtXi
    rows.append((nm,len(s),net,net-base_net,beta[1]*100,beta[1]/np.sqrt(V[1,1])))
print(pd.DataFrame(rows,columns=['strategy','trades','ABS net20%','minus BULL baseline','diff%','t_diff']
      ).sort_values('diff%',ascending=False).to_string(index=False,float_format=lambda x:f"{x:.2f}"))

print()
print("=== the three survivors, by YEAR within BULL (is it just 2025 again?) ===")
surv=['Episodic Pivot (gap>=5%, 3x vol)','Resistance breakout','TREND REGIME (spec 002 entry)']
out=[]
for nm in surv:
    m=(P[nm]&d.liq&(d.rg=='BULL')).fillna(False)
    s=d[m&d.fo20.notna()&(d.bad20.fillna(1)==0)].copy(); s['yr']=s.date.dt.year
    r={'strategy':nm,'N':len(s)}
    for y in sorted(s.yr.unique()):
        gg=s[s.yr==y]
        r[y]=((gg.fo20-COST)*100).mean() if len(gg)>=10 else np.nan
        r[f'n{y}']=len(gg)
    out.append(r)
O=pd.DataFrame(out)
yrs=[c for c in O.columns if isinstance(c,(int,np.integer))]
print(O[['strategy','N']+sorted(yrs)].to_string(index=False,float_format=lambda x:f"{x:.1f}"))
print()
print("trade counts per year:")
print(O[['strategy']+[f'n{y}' for y in sorted(yrs)]].to_string(index=False))
