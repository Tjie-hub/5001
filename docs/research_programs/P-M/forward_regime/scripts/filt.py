import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',250)
COST=0.006
d=pd.read_pickle(f"{SP}/ma.pkl")
raw=pd.read_pickle(f"{SP}/ohlcv.pkl"); ih=raw[raw.ticker=='IHSG'].set_index('date')['close'].to_dict()
d=d[d.ticker!='IHSG'].sort_values(['ticker','date']).reset_index(drop=True)
g=d.groupby('ticker',sort=False)
d['sl']=g['slope'].shift(1); d['er']=g['ER'].shift(1); d['pa']=g['pct_above'].shift(1)
d['UP']=((d.sl>0.02)&(d.er>=0.30)&(d.pa>=0.70)).fillna(False).astype(bool)
d['nz']=(d.volume>0).astype(int)
d['nz20']=g['nz'].transform(lambda s:s.shift(1).rolling(20,min_periods=20).sum())
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)&(d.volume>0)&(d.nz20>=18)).fillna(False).astype(bool)
d['ext']=d.close/d.ema20-1            # extension above EMA20 at entry
d['atrp']=d.atr14/d.close             # volatility
tr=[]
for tk,x in d.groupby('ticker',sort=False):
    up=x.UP.values; lq=x.liq.values
    if not up.any(): continue
    cl=x.close.values;hi=x.high.values;at=x.atr14.values;dt=x.date.values;bad=x.bad.values;N=len(x)
    st=np.where(up & ~np.r_[False,up[:-1]] & lq & ~np.isnan(at))[0]
    for i in st:
        peak=hi[i]; j=min(i+60,N-1)
        for k in range(1,min(60,N-1-i)+1):
            p=i+k; peak=max(peak,hi[p])
            if cl[p]<peak-3*at[p]: j=p; break
        if bad[i+1:j+1].sum()>0: continue
        ie=ih.get(pd.Timestamp(dt[i])); ix=ih.get(pd.Timestamp(dt[j]))
        if ie is None or ix is None: continue
        tr.append((tk,dt[i],cl[j]/cl[i]-1-COST,ix/ie-1,x.sl.values[i],x.er.values[i],x.ext.values[i],x.atrp.values[i]))
T=pd.DataFrame(tr,columns=['ticker','date','net','mkt','sl','er','ext','atrp'])
T['exc']=T.net-T.mkt; T['yr']=pd.DatetimeIndex(T.date).year
T.to_pickle(f"{SP}/trades002.pkl")
IS=T.yr<=2023; OOS=T.yr>=2024; EX25=T.yr!=2025
# cuts learned on IS ONLY (no peeking at OOS)
q80=T.loc[IS,'sl'].quantile(.80); q60=T.loc[IS,'sl'].quantile(.60)
e80=T.loc[IS,'ext'].quantile(.80); a80=T.loc[IS,'atrp'].quantile(.80)
print("cuts fitted on IS (2021-23) only: slope Q80=%.3f Q60=%.3f | ext Q80=%.3f | atr%% Q80=%.3f"%(q80,q60,e80,a80))
def rep(nm,m):
    out=[nm,int(m.sum())]
    for lbl,sub in [('FULL',m),('IS',m&IS),('OOS',m&OOS),('EX25',m&EX25)]:
        s=T[sub]
        if len(s)<50: out+= [np.nan,np.nan]; continue
        mu,t=cluster_t(s.exc.values,s.date.values); out+=[mu*100,t]
    s=T[m]; out+=[100*(s.net>0).mean()]
    return out
rows=[rep('F0 none (= spec 002)',pd.Series(True,index=T.index)),
      rep('F1 drop slope Q5',T.sl<q80),
      rep('F2 drop slope Q4+Q5',T.sl<q60),
      rep('F3 drop extension Q5',T.ext<e80),
      rep('F4 drop volatility Q5',T.atrp<a80),
      rep('F5 F1 + F3',(T.sl<q80)&(T.ext<e80))]
print(pd.DataFrame(rows,columns=['filter','N','FULL%','t','IS%','t','OOS%','t','EX25%','t','win%']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
