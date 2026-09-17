import os,sys; sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'.')
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.environ['SP']; pd.set_option('display.width',260)
from engine.sector_rotation import TICKER_SECTOR_MAP as TS
d=pd.read_pickle(f"{SP}/ma.pkl"); g=d.groupby('ticker',sort=False)
d['sl']=g['slope'].shift(1); d['er']=g['ER'].shift(1); d['pa']=g['pct_above'].shift(1)
d['UP']=((d.sl>0.02)&(d.er>=0.30)&(d.pa>=0.70)).fillna(False)
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)).fillna(False)
d=d[d.ticker!='IHSG']
# re-simulate atr3 keeping ENTRY and EXIT dates
hold=[]
for tk,x in d.groupby('ticker',sort=False):
    up=x.UP.values; lq=x.liq.values
    if up.sum()==0: continue
    cl=x.close.values; hi=x.high.values; at=x.atr14.values; dt=x.date.values; N=len(x)
    st=np.where(up & ~np.r_[False,up[:-1]] & lq & ~np.isnan(at))[0]
    for i in st:
        peakh=hi[i]; j=min(i+60,N-1)
        for k in range(1,min(60,N-1-i)+1):
            p=i+k; peakh=max(peakh,hi[p])
            if cl[p]<peakh-3*at[p]: j=p; break
        hold.append((tk,dt[i],dt[j]))
H=pd.DataFrame(hold,columns=['ticker','ent','ext'])
print("atr3 positions:",len(H))
cal=np.sort(d.date.unique())
ret=d.pivot_table(index='date',columns='ticker',values='ret')
# occupancy per calendar day
occ={}
for tk,a,b in H.itertuples(index=False):
    for dd in cal[(cal>=a)&(cal<=b)]: occ.setdefault(dd,[]).append(tk)
cnt=pd.Series({k:len(v) for k,v in occ.items()}).sort_index()
print("concurrent positions: mean %.0f  median %.0f  p90 %.0f"%(cnt.mean(),cnt.median(),cnt.quantile(.9)))
# avg pairwise correlation among concurrently-held names (sampled dates)
samp=[k for k in sorted(occ) if len(occ[k])>=10][::25]
rhos=[];secs=[]
for k in samp:
    names=[t for t in occ[k] if t in ret.columns]
    if len(names)<10: continue
    w=ret.loc[:k, names].tail(60).dropna(axis=1,thresh=40)
    if w.shape[1]<10: continue
    C=w.corr().values; iu=np.triu_indices_from(C,1)
    rhos.append(np.nanmean(C[iu]))
    m=[TS.get(t) for t in w.columns if t in TS]
    if len(m)>=5: secs.append(pd.Series(m).value_counts(normalize=True).max())
rho=float(np.nanmean(rhos))
n=cnt.mean(); neff=n/(1+(n-1)*rho)
print("\n=== EFFECTIVE BREADTH ===")
print("avg pairwise corr of concurrently-held names: rho = %.3f  (%d sample dates)"%(rho,len(rhos)))
print("nominal positions N = %.0f  ->  EFFECTIVE N = %.1f"%(n,neff))
print("i.e. %.0f positions behave like ~%.0f independent bets"%(n,neff))
if secs: print("\nmax single-sector share among concurrent (mapped only): mean %.0f%%  p90 %.0f%%"%(100*np.mean(secs),100*np.quantile(secs,.9)))
# benchmark: rho for a random basket of liquid names
liqn=[c for c in ret.columns if d[d.ticker==c].liq.mean()>0.5][:300]
rr=[]
for k in samp[:40]:
    w=ret.loc[:k,liqn].tail(60).dropna(axis=1,thresh=40)
    if w.shape[1]<10: continue
    sel=list(w.columns[:40]); C=w[sel].corr().values; iu=np.triu_indices_from(C,1); rr.append(np.nanmean(C[iu]))
print("baseline rho for a random liquid basket: %.3f"%float(np.nanmean(rr)))
