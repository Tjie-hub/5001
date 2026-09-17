import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']
COST=0.006
d=pd.read_pickle(f"{SP}/ma.pkl")
raw=pd.read_pickle(f"{SP}/ohlcv.pkl"); ihs=raw[raw.ticker=='IHSG'].set_index('date')['close'].sort_index().to_dict()
d=d[d.ticker!='IHSG'].sort_values(['ticker','date']).reset_index(drop=True)
g=d.groupby('ticker',sort=False)
d['sl']=g['slope'].shift(1); d['er']=g['ER'].shift(1); d['pa']=g['pct_above'].shift(1)
d['UP']=((d.sl>0.02)&(d.er>=0.30)&(d.pa>=0.70)).fillna(False).astype(bool)
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)).fillna(False).astype(bool)
d['nz']=(d.volume>0).astype(int)
d['nz20']=d.groupby('ticker',sort=False)['nz'].transform(lambda s:s.shift(1).rolling(20,min_periods=20).sum())
tr=[]
for tk,x in d.groupby('ticker',sort=False):
    up=x.UP.values; lq=x.liq.values; nz=x.nz.values; nz20=x.nz20.values
    if not up.any(): continue
    cl=x.close.values; hi=x.high.values; at=x.atr14.values; dt=x.date.values; bad=x.bad.values; N=len(x)
    st=np.where(up & ~np.r_[False,up[:-1]] & lq & ~np.isnan(at) & (nz==1) & (nz20>=18))[0]
    for i in st:
        peak=hi[i]; j=min(i+60,N-1)
        for k in range(1,min(60,N-1-i)+1):
            p=i+k; peak=max(peak,hi[p])
            if cl[p]<peak-3*at[p]: j=p; break
        if bad[i+1:j+1].sum()>0: continue
        ie=ihs.get(pd.Timestamp(dt[i])); ix=ihs.get(pd.Timestamp(dt[j]))
        if ie is None or ix is None: continue
        tr.append((dt[i],cl[j]/cl[i]-1-COST,ix/ie-1))
T=pd.DataFrame(tr,columns=['date','net','mkt']); T['exc']=T.net-T.mkt
T['yr']=pd.DatetimeIndex(T.date).year
print("FWD-PM-REGIME-002 reference (V2 guard):")
for nm,S in [('FULL',T),('EX-2025',T[T.yr!=2025])]:
    mu,t=cluster_t(S.exc.values,S.date.values); nd=pd.Series(S.date).nunique()
    se=mu/t
    need=nd*(se/(mu/(1.645+0.842)))**2
    print("  %-8s N=%d clusters=%d mean=%+.3f%% SE=%.3f%% t=%.2f  -> n=%.0f days (%.1f months) for 80%% power"%(
        nm,len(S),nd,100*mu,100*se,t,need,need/21))
print("\n  (spec 001 was: FULL +2.260%% t=6.45 ; EX-2025 +1.106%% SE 0.330%% t=3.35 -> 24.5 months)")
