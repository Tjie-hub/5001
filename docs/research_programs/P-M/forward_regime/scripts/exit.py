import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.environ['SP']
d=pd.read_pickle(f"{SP}/ma.pkl"); g=d.groupby('ticker',sort=False)
d['sl']=g['slope'].shift(1); d['er']=g['ER'].shift(1); d['pa']=g['pct_above'].shift(1)
d['UP']=((d.sl>0.02)&(d.er>=0.30)&(d.pa>=0.70)).fillna(False)
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)).fillna(False)
_r=pd.read_pickle(f"{SP}/ohlcv.pkl"); ih=_r[_r.ticker=='IHSG'].set_index('date')['close']
d=d[d.ticker!='IHSG'].sort_values(['ticker','date']).reset_index(drop=True)
ihm=ih.to_dict()
COST=0.006; MAXH=60
recs=[]
for tk,x in d.groupby('ticker',sort=False):
    up=x.UP.values; lq=x.liq.values
    if up.sum()==0: continue
    cl=x.close.values; hi=x.high.values; lo=x.low.values
    em=x.ema20.values; vw=x.vwma20.values; at=x.atr14.values
    slv=x.sl.values; dt=x.date.values; N=len(x)
    # episode starts: UP goes False->True, and liquid, and tradable
    starts=np.where(up & ~np.r_[False,up[:-1]] & lq & ~np.isnan(at) & ~np.isnan(vw))[0]
    for i in starts:
        if i+1>=N: continue
        ent=cl[i]; peak=cl[i]; peakh=hi[i]
        ex={}
        for k in range(1,min(MAXH,N-1-i)+1):
            j=i+k; c=cl[j]
            peak=max(peak,c); peakh=max(peakh,hi[j])
            if 'flip' not in ex and not up[j]:            ex['flip']=(j,c)
            if 'ema'  not in ex and c<em[j]:              ex['ema']=(j,c)
            if 'vwma' not in ex and c<vw[j]:              ex['vwma']=(j,c)
            if 'atr2' not in ex and c<peakh-2*at[j]:      ex['atr2']=(j,c)
            if 'atr3' not in ex and c<peakh-3*at[j]:      ex['atr3']=(j,c)
            if 'stop8'not in ex and c<ent*0.92:           ex['stop8']=(j,c)
            if 'ema_or_stop' not in ex and (c<em[j] or c<ent*0.92): ex['ema_or_stop']=(j,c)
        cap=min(i+MAXH,N-1); h20=min(i+20,N-1)
        ex['hold20']=(h20,cl[h20]); ex['hold60']=(cap,cl[cap])
        for r in ['flip','ema','vwma','atr2','atr3','stop8','ema_or_stop']:
            if r not in ex: ex[r]=(cap,cl[cap])
        base=ihm.get(pd.Timestamp(dt[i]),np.nan)
        for r,(j,px) in ex.items():
            mb=ihm.get(pd.Timestamp(dt[j]),np.nan)
            mk=(mb/base-1) if (base==base and mb==mb) else np.nan
            mae=lo[i+1:j+1].min()/ent-1 if j>i else 0.0
            recs.append((tk,dt[i],r,px/ent-1-COST,mk,j-i,mae,slv[i]))
R=pd.DataFrame(recs,columns=['ticker','date','rule','net','mkt','days','mae','slope'])
R.to_pickle(f"{SP}/trades.pkl")
print("episodes:",R[R.rule=='hold20'].shape[0],"| tickers:",R.ticker.nunique())
