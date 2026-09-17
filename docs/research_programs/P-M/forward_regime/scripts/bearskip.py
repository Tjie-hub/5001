import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings, collections; warnings.filterwarnings('ignore')
SP=os.environ['SP']; pd.set_option('display.width',250)
BUY,SELL=0.0025,0.0035
d=pd.read_pickle(f"{SP}/ma.pkl").sort_values(['ticker','date']).reset_index(drop=True)
raw=pd.read_pickle(f"{SP}/ohlcv.pkl"); ihs=raw[raw.ticker=='IHSG'].set_index('date')['close'].sort_index()
RG=pd.read_pickle(f"{SP}/ihsg_regime.pkl"); rgm=dict(zip(RG.date,RG.regime))
d=d[d.ticker!='IHSG'].reset_index(drop=True); g=d.groupby('ticker',sort=False)
d['sl']=g['slope'].shift(1); d['er']=g['ER'].shift(1); d['pa']=g['pct_above'].shift(1)
d['UP']=((d.sl>0.02)&(d.er>=0.30)&(d.pa>=0.70)).fillna(False).astype(bool)
d['nz']=(d.volume>0).astype(int); d['nz20']=g['nz'].transform(lambda s:s.shift(1).rolling(20,min_periods=20).sum())
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)&(d.volume>0)&(d.nz20>=18)).fillna(False).astype(bool)
cal=np.sort(d.date.unique()); ret=d.pivot_table(index='date',columns='ticker',values='ret').sort_index()
pos=[]
for tk,x in d.groupby('ticker',sort=False):
    up=x.UP.values; lq=x.liq.values
    if not up.any(): continue
    cl=x.close.values;hi=x.high.values;at=x.atr14.values;dt=x.date.values;N=len(x)
    for i in np.where(up & ~np.r_[False,up[:-1]] & lq & ~np.isnan(at))[0]:
        peak=hi[i]; j=min(i+60,N-1)
        for k in range(1,min(60,N-1-i)+1):
            p=i+k; peak=max(peak,hi[p])
            if cl[p]<peak-3*at[p]: j=p; break
        pos.append((tk,dt[i],dt[j],rgm.get(pd.Timestamp(dt[i]),'NA')))
P=pd.DataFrame(pos,columns=['ticker','ent','ext','rg'])
def run(sub):
    hold=collections.defaultdict(list); e1=collections.defaultdict(list); e2=collections.defaultdict(list)
    for tk,a,b in sub[['ticker','ent','ext']].itertuples(index=False):
        for dd in cal[(cal>a)&(cal<=b)]: hold[dd].append(tk)
        e1[a].append(tk); e2[b].append(tk)
    rr=[]
    for dd in cal:
        nm=hold.get(dd,[]); n=len(nm)
        if n==0: rr.append(0.0); continue
        r=np.nanmean(ret.loc[dd,nm].values); w=1.0/n
        c=w*BUY*len([t for t in e1.get(dd,[]) if t in nm])+w*SELL*len([t for t in e2.get(dd,[]) if t in nm])
        rr.append((0.0 if np.isnan(r) else r)-c)
    return pd.Series(rr,index=cal)
ihr=ihs.reindex(cal).pct_change().fillna(0); msk=pd.DatetimeIndex(cal).year!=2025
def st(s,nm):
    eq=(1+s).cumprod(); y=len(s)/252
    return (nm,100*(eq.iloc[-1]**(1/y)-1),100*((1+s[msk]).cumprod().iloc[-1]**(252/msk.sum())-1),
            s.std()*np.sqrt(252)*100, s.mean()/s.std()*np.sqrt(252),100*(eq/eq.cummax()-1).min())
rows=[st(run(P),'ALL regimes (spec 002)'),
      st(run(P[P.rg!='BEAR']),'SKIP entries in BEAR'),
      st(run(P[P.rg=='BULL']),'BULL entries only'),
      st(ihr,'IHSG buy & hold')]
print("=== ABSOLUTE return (what you actually eat), not excess ===")
print(pd.DataFrame(rows,columns=['book','CAGR%','CAGR ex25%','Vol%','Sharpe','MaxDD%']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
