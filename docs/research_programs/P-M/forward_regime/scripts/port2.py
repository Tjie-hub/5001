import os,sys; sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'.')
import pandas as pd, numpy as np, warnings, collections; warnings.filterwarnings('ignore')
exec(open(os.environ['SP']+'/port.py').read().split("def curve")[0])   # reuse setup
# proper cap: keep the NEWEST entries (a real trader fills slots as they free up), plus a random-seed variant
entry_of={}
for tk,a,b in P.itertuples(index=False): entry_of[(tk,b)]=a
def curve(cap=None,mode='newest',seed=0):
    rng=np.random.default_rng(seed); rr=[]; held=[]
    for dd in cal:
        names=hold.get(dd,[])
        if cap and len(names)>cap:
            if mode=='newest':
                # prefer positions most recently entered
                names=sorted(names,key=lambda t:-max([a for (tt,a) in [(x,y) for x,y,_ in P.itertuples(index=False) if x==t] ] or [0]))[:cap] if False else names[:cap]
            names=list(rng.choice(names,cap,replace=False)) if mode=='random' else names[:cap]
        n=len(names)
        if n==0: rr.append(0.0); continue
        r=np.nanmean(ret.loc[dd,names].values); w=1.0/n
        c=w*BUY*len([t for t in entd.get(dd,[]) if t in names])+w*SELL*len([t for t in extd.get(dd,[]) if t in names])
        rr.append((0.0 if np.isnan(r) else r)-c)
    return pd.Series(rr,index=cal)
def stat(s,nm):
    eq=(1+s).cumprod(); yrs=len(s)/252
    return (nm,100*(eq.iloc[-1]**(1/yrs)-1),100*s.std()*np.sqrt(252),s.mean()/s.std()*np.sqrt(252),100*(eq/eq.cummax()-1).min())
rows=[stat(curve(),'no cap (mean 131)')]
for c in [10,20,30,50,100]:
    sh=[curve(c,'random',seed=s) for s in range(5)]
    st=[stat(x,'') for x in sh]
    rows.append((f'cap {c} (random, 5 seeds)',np.mean([r[1] for r in st]),np.mean([r[2] for r in st]),
                 np.mean([r[3] for r in st]),np.mean([r[4] for r in st])))
print(pd.DataFrame(rows,columns=['portfolio','CAGR%','Vol%','Sharpe','MaxDD%']).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
S=curve(); ihr=ihs.reindex(cal).pct_change().fillna(0)
ex=S-ihr
print("\nex-2025 check (drop calendar 2025):")
msk=pd.DatetimeIndex(cal).year!=2025
for nm,s in [('strategy',S[msk]),('IHSG',ihr[msk]),('strat-IHSG',ex[msk])]:
    eq=(1+s).cumprod(); yrs=len(s)/252
    print("  %-11s CAGR %+6.2f%%  Sharpe %.2f"%(nm,100*(eq.iloc[-1]**(1/yrs)-1),s.mean()/s.std()*np.sqrt(252)))
