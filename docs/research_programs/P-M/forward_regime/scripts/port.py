import os,sys; sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'.')
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.environ['SP']; pd.set_option('display.width',260)
BUY,SELL=0.0025,0.0035          # engine/exits/costs.py: comm+slippage per leg
d=pd.read_pickle(f"{SP}/ma.pkl"); g=d.groupby('ticker',sort=False)
d['sl']=g['slope'].shift(1); d['er']=g['ER'].shift(1); d['pa']=g['pct_above'].shift(1)
d['UP']=((d.sl>0.02)&(d.er>=0.30)&(d.pa>=0.70)).fillna(False)
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)).fillna(False)
ihs=pd.read_pickle(f"{SP}/ohlcv.pkl"); ihs=ihs[ihs.ticker=='IHSG'].set_index('date')['close']
d=d[d.ticker!='IHSG']
pos=[]; last_bar_exits=0
for tk,x in d.groupby('ticker',sort=False):
    up=x.UP.values; lq=x.liq.values
    if up.sum()==0: continue
    cl=x.close.values; hi=x.high.values; at=x.atr14.values; dt=x.date.values; N=len(x)
    st=np.where(up & ~np.r_[False,up[:-1]] & lq & ~np.isnan(at))[0]
    for i in st:
        peakh=hi[i]; j=min(i+60,N-1); hit=False
        for k in range(1,min(60,N-1-i)+1):
            p=i+k; peakh=max(peakh,hi[p])
            if cl[p]<peakh-3*at[p]: j=p; hit=True; break
        if j==N-1 and not hit: last_bar_exits+=1
        pos.append((tk,dt[i],dt[j]))
P=pd.DataFrame(pos,columns=['ticker','ent','ext'])
print("positions:",len(P),"| exits at ticker's last bar (delisting-optimistic):",last_bar_exits)
ret=d.pivot_table(index='date',columns='ticker',values='ret').sort_index()
cal=ret.index.values
# holdings: position contributes returns for dates in (ent, ext]
import collections
hold=collections.defaultdict(list); entd=collections.defaultdict(list); extd=collections.defaultdict(list)
for tk,a,b in P.itertuples(index=False):
    sel=cal[(cal>a)&(cal<=b)]
    for dd in sel: hold[dd].append(tk)
    entd[a].append(tk); extd[b].append(tk)
def curve(cap=None):
    rr=[]
    for dd in cal:
        names=hold.get(dd,[])
        if cap and len(names)>cap: names=names[:cap]
        n=len(names)
        if n==0: rr.append(0.0); continue
        r=np.nanmean(ret.loc[dd,names].values)
        w=1.0/n
        c=w*BUY*len([t for t in entd.get(dd,[]) if t in names])+w*SELL*len([t for t in extd.get(dd,[]) if t in names])
        rr.append((0.0 if np.isnan(r) else r)-c)
    return pd.Series(rr,index=cal)
def stat(s,nm):
    eq=(1+s).cumprod(); yrs=len(s)/252
    cagr=eq.iloc[-1]**(1/yrs)-1; vol=s.std()*np.sqrt(252); sh=s.mean()/s.std()*np.sqrt(252) if s.std()>0 else np.nan
    dd=(eq/eq.cummax()-1).min()
    return (nm,100*cagr,100*vol,sh,100*dd,100*(eq.iloc[-1]-1))
S=curve(); S30=curve(30)
ihr=ihs.reindex(cal).pct_change().fillna(0)
rows=[stat(S,'STRATEGY (all positions)'),stat(S30,'STRATEGY (cap 30)'),stat(ihr,'IHSG buy&hold'),stat(S-ihr,'STRATEGY minus IHSG')]
print("\n"+pd.DataFrame(rows,columns=['','CAGR%','Vol%','Sharpe','MaxDD%','Total%']).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
yr=pd.DataFrame({'strat':S,'ihsg':ihr}).groupby(pd.DatetimeIndex(cal).year).apply(lambda x:pd.Series({'strat%':100*((1+x.strat).prod()-1),'ihsg%':100*((1+x.ihsg).prod()-1)}))
print("\n=== by year ===\n"+yr.to_string(float_format=lambda x:f"{x:.2f}"))
