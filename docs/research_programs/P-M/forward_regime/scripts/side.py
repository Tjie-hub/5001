import os,sys; sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'.')
import pandas as pd, numpy as np, warnings, collections; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',260)
COST=0.006
d=pd.read_pickle(f"{SP}/ma.pkl"); g=d.groupby('ticker',sort=False)
d['sl']=g['slope'].shift(1); d['er']=g['ER'].shift(1); d['pa']=g['pct_above'].shift(1); d['cr']=g['cross'].shift(1)
d['SIDE']=((d.sl.abs()<0.01)&(d.er<0.20)&(d.cr>=4)).fillna(False)
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)).fillna(False)
d['hi20']=g['high'].transform(lambda s:s.rolling(20,min_periods=20).max()).groupby(d.ticker).shift(1)
d['lo20']=g['low'].transform(lambda s:s.rolling(20,min_periods=20).min()).groupby(d.ticker).shift(1)
d['rng']=(d.hi20-d.lo20)/d.close
raw=pd.read_pickle(f"{SP}/ohlcv.pkl"); ihs=raw[raw.ticker=='IHSG'].set_index('date')['close'].sort_index()
d=d[d.ticker!='IHSG']
print("SIDEWAYS liquid days:",int((d.SIDE&d.liq).sum()),"| median 20d range as %% of price: %.1f%%"%(100*d[d.SIDE&d.liq].rng.median()))
recs=[]
for ENTQ,TGT,STOP,MAXD in [(0.25,0.75,0.97,10),(0.25,0.60,0.97,10),(0.20,0.80,0.95,15),(0.30,0.70,0.95,10),(0.25,0.50,0.97,5)]:
    trades=[]
    for tk,x in d.groupby('ticker',sort=False):
        m=(x.SIDE&x.liq&x.rng.notna()).values
        if m.sum()==0: continue
        cl=x.close.values; lo=x.low.values; hi=x.high.values; L=x.lo20.values; H=x.hi20.values; dt=x.date.values; N=len(x)
        band=(cl-L)/(H-L)
        sig=np.where(m&(band<=ENTQ)&np.isfinite(band))[0]
        last=-99
        for i in sig:
            if i-last<MAXD or i+1>=N: continue
            last=i; ent=cl[i]; tgt=L[i]+TGT*(H[i]-L[i]); stp=ent*STOP
            j=min(i+MAXD,N-1); px=cl[j]
            for k in range(1,min(MAXD,N-1-i)+1):
                p=i+k
                if cl[p]>=tgt: j,px=p,cl[p]; break
                if cl[p]<=stp: j,px=p,cl[p]; break
            trades.append((dt[i],dt[j],px/ent-1-COST,j-i))
    T=pd.DataFrame(trades,columns=['ent','ext','net','days'])
    if len(T)<50: continue
    ihd=ihs.to_dict()
    T['mkt']=[ (ihd.get(pd.Timestamp(b),np.nan)/ihd.get(pd.Timestamp(a),np.nan)-1) for a,b in zip(T.ent,T.ext)]
    T=T[T.mkt.notna()]
    mu,t=cluster_t((T.net-T.mkt).values,T.ent.values)
    recs.append((f'buy<{ENTQ:.2f} tgt{TGT:.2f} stop{STOP} max{MAXD}d',len(T),100*T.net.mean(),100*T.net.median(),
                 mu*100,t,100*(T.net>0).mean(),T.days.mean()))
print("\n=== SIDEWAYS mean-reversion: buy lower band, sell upper (net of 0.60% RT) ===")
print(pd.DataFrame(recs,columns=['spec','N','net%','med%','exc%','t','win%','days']).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
