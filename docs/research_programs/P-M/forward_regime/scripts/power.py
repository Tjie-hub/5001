import os,sys; sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'.')
import pandas as pd, numpy as np, warnings, collections; warnings.filterwarnings('ignore')
exec(open(os.environ['SP']+'/port.py').read().split("def curve")[0])
def curve(cap=None,seed=0):
    rng=np.random.default_rng(seed); rr=[]
    for dd in cal:
        names=hold.get(dd,[])
        if cap and len(names)>cap: names=list(rng.choice(names,cap,replace=False))
        n=len(names)
        if n==0: rr.append(0.0); continue
        r=np.nanmean(ret.loc[dd,names].values); w=1.0/n
        c=w*BUY*len([t for t in entd.get(dd,[]) if t in names])+w*SELL*len([t for t in extd.get(dd,[]) if t in names])
        rr.append((0.0 if np.isnan(r) else r)-c)
    return pd.Series(rr,index=cal)
S=curve(); ihr=ihs.reindex(cal).pct_change().fillna(0)
M=pd.DataFrame({'s':S,'m':ihr}).groupby(pd.DatetimeIndex(cal).to_period('M')).apply(
    lambda x: pd.Series({'s':(1+x.s).prod()-1,'m':(1+x.m).prod()-1}))
M['inc']=M.s-M.m
full=M.inc; ex25=M[M.index.year!=2025].inc
for nm,v in [('FULL sample',full),('EX-2025 (planning basis)',ex25)]:
    t=v.mean()/ (v.std()/np.sqrt(len(v)))
    print("%-24s n=%d  mean=%+.3f%%/mo  sd=%.3f%%  t=%.2f  P(>0)=%.0f%%"%(nm,len(v),100*v.mean(),100*v.std(),t,100*(v>0).mean()))
sd=ex25.std()
print("\n=== power one-sided alpha 0.05, 80pct, ex-2025 sd=%.3f pct/mo ==="%(100*sd))
for n in [12,18,24,30,36]:
    se=sd/np.sqrt(n); mde=(1.645+0.842)*se
    print("  n=%2d  SE=%.3f%%  MDE=%+.3f%%/mo"%(n,100*se,100*mde))
print("\nex-2025 mean incremental = %+.3f%%/mo -> n needed = %d months"%(100*ex25.mean(),int(np.ceil(((1.645+0.842)*sd/ex25.mean())**2))))
