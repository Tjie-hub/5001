import os,sys; sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'.')
import pandas as pd, numpy as np, warnings, collections, pickle; warnings.filterwarnings('ignore')
SP=os.environ['SP']; pd.set_option('display.width',260)
BUY,SELL=0.0025,0.0035
d=pd.read_pickle(f"{SP}/ma.pkl"); g=d.groupby('ticker',sort=False)
d['sl']=g['slope'].shift(1); d['er']=g['ER'].shift(1); d['pa']=g['pct_above'].shift(1)
d['UP']=((d.sl>0.02)&(d.er>=0.30)&(d.pa>=0.70)).fillna(False)
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)).fillna(False)
raw=pd.read_pickle(f"{SP}/ohlcv.pkl"); ihs=raw[raw.ticker=='IHSG'].set_index('date')['close'].sort_index()
# --- MARKET regime from IHSG itself ---
ie=ihs.ewm(span=20,adjust=False,min_periods=20).mean()
mkt=pd.DataFrame({'c':ihs,'e':ie}); mkt['above']=mkt.c>mkt.e
mkt['slope']=mkt.e/mkt.e.shift(10)-1
mkt['OK']=(mkt.above&(mkt.slope>-0.005)).shift(1).fillna(False)   # lagged: known at entry
MOK=mkt.OK.to_dict()
d=d[d.ticker!='IHSG']
cal=np.sort(d.date.unique()); ret=d.pivot_table(index='date',columns='ticker',values='ret').sort_index()
MULTS=[3,4,5,6]
pos={m:[] for m in MULTS}; pos_mf={m:[] for m in MULTS}
for tk,x in d.groupby('ticker',sort=False):
    up=x.UP.values; lq=x.liq.values
    if up.sum()==0: continue
    cl=x.close.values; hi=x.high.values; at=x.atr14.values; dt=x.date.values; N=len(x)
    st=np.where(up & ~np.r_[False,up[:-1]] & lq & ~np.isnan(at))[0]
    for i in st:
        mok=MOK.get(pd.Timestamp(dt[i]),False)
        peakh=hi[i]; done={}
        for k in range(1,min(90,N-1-i)+1):
            p=i+k; peakh=max(peakh,hi[p])
            for m in MULTS:
                if m not in done and cl[p]<peakh-m*at[p]: done[m]=p
            if len(done)==len(MULTS): break
        for m in MULTS:
            j=done.get(m,min(i+90,N-1))
            pos[m].append((tk,dt[i],dt[j]))
            if mok: pos_mf[m].append((tk,dt[i],dt[j]))
pickle.dump({'pos':pos,'pos_mf':pos_mf,'cal':cal},open(f"{SP}/pol.pkl","wb"))
def run(P):
    hold=collections.defaultdict(list); entd=collections.defaultdict(list); extd=collections.defaultdict(list)
    for tk,a,b in P:
        for dd in cal[(cal>a)&(cal<=b)]: hold[dd].append(tk)
        entd[a].append(tk); extd[b].append(tk)
    rr=[]
    for dd in cal:
        nm=hold.get(dd,[]); n=len(nm)
        if n==0: rr.append(0.0); continue
        r=np.nanmean(ret.loc[dd,nm].values); w=1.0/n
        c=w*BUY*len([t for t in entd.get(dd,[]) if t in nm])+w*SELL*len([t for t in extd.get(dd,[]) if t in nm])
        rr.append((0.0 if np.isnan(r) else r)-c)
    return pd.Series(rr,index=cal),np.mean([len(v) for v in hold.values()])
ihr=ihs.reindex(cal).pct_change().fillna(0); msk=pd.DatetimeIndex(cal).year!=2025
def cg(s): eq=(1+s).cumprod(); return 100*(eq.iloc[-1]**(252/len(s))-1)
rows=[]
for tag,PS in [('no mkt filter',pos),('+ IHSG downtrend filter',pos_mf)]:
    for m in MULTS:
        P=PS[m]; S,npos=run(P); e=S-ihr
        hd=np.mean([(pd.Timestamp(b)-pd.Timestamp(a)).days for _,a,b in P])
        rows.append((tag,f'{m}xATR',len(P),npos,hd,252*(len(P)/len(cal))/npos,cg(e),cg(e[msk]),
                     e.mean()/e.std()*np.sqrt(252),100*((1+S).cumprod()/(1+S).cumprod().cummax()-1).min()))
print(pd.DataFrame(rows,columns=['filter','exit','trades','pos','hold_d','turns/yr','exc CAGR%','exc ex25%','Sharpe','MaxDD%']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
