import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',270)
BUY,SELL=0.0025,0.0035
d=pd.read_pickle(f"{SP}/ma.pkl").sort_values(['ticker','date']).reset_index(drop=True)
raw=pd.read_pickle(f"{SP}/ohlcv.pkl"); ih=raw[raw.ticker=='IHSG'].set_index('date')['close'].to_dict()
d=d[d.ticker!='IHSG'].reset_index(drop=True)
g=d.groupby('ticker',sort=False)
d['sl']=g['slope'].shift(1); d['er']=g['ER'].shift(1); d['pa']=g['pct_above'].shift(1)
d['UP']=((d.sl>0.02)&(d.er>=0.30)&(d.pa>=0.70)).fillna(False).astype(bool)
d['nz']=(d.volume>0).astype(int)
d['nz20']=g['nz'].transform(lambda s:s.shift(1).rolling(20,min_periods=20).sum())
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)&(d.volume>0)&(d.nz20>=18)).fillna(False).astype(bool)
ew=d[d.liq].groupby('date')['ret'].mean(); ewi=(1+ew.fillna(0)).cumprod().to_dict()
tr=[]
for tk,x in d.groupby('ticker',sort=False):
    up=x.UP.values; lq=x.liq.values
    if not up.any(): continue
    cl=x.close.values; op=x.open.values; hi=x.high.values; at=x.atr14.values
    dt=x.date.values; bad=x.bad.values; N=len(x)
    st=np.where(up & ~np.r_[False,up[:-1]] & lq & ~np.isnan(at))[0]
    for i in st:
        if i+1>=N: continue
        peak=hi[i]; j=min(i+60,N-1)
        for k in range(1,min(60,N-1-i)+1):
            p=i+k; peak=max(peak,hi[p])
            if cl[p]<peak-3*at[p]: j=p; break
        if j<=i or bad[i+1:j+1].sum()>0: continue
        ie=ih.get(pd.Timestamp(dt[i])); ix=ih.get(pd.Timestamp(dt[j]))
        ee=ewi.get(pd.Timestamp(dt[i])); ex=ewi.get(pd.Timestamp(dt[j]))
        if None in (ie,ix,ee,ex): continue
        # A: entry at signal close (as specced) ; B: entry at NEXT open (execution-realistic)
        rA=cl[j]/cl[i]-1-BUY-SELL
        rB=cl[j]/op[i+1]-1-BUY-SELL
        tr.append((dt[i],rA,rB,ix/ie-1,ex/ee-1))
T=pd.DataFrame(tr,columns=['date','rA','rB','mkt','ewb'])
T['yr']=pd.DatetimeIndex(T.date).year
print("trades:",len(T))
rows=[]
for nm,r,b in [('A close entry  vs IHSG','rA','mkt'),
               ('B NEXT-OPEN    vs IHSG','rB','mkt'),
               ('C close entry  vs EW-book','rA','ewb'),
               ('D NEXT-OPEN    vs EW-book','rB','ewb')]:
    for lbl,S in [('FULL',T),('EX-2025',T[T.yr!=2025])]:
        mu,t=cluster_t((S[r]-S[b]).values,S.date.values)
        rows.append((nm,lbl,len(S),100*S[r].mean(),mu*100,t))
print(pd.DataFrame(rows,columns=['spec','basis','N','net/trade%','excess/trade%','t']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
print("\n>>> spec 002's frozen reference is row A/EX-2025 = +0.928%, t 2.83")
