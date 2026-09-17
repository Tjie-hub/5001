import os,sys; sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'.')
import pandas as pd, numpy as np, warnings, collections; warnings.filterwarnings('ignore')
exec(open(os.environ['SP']+'/port.py').read().split("def curve")[0])
def curve(buy,sell):
    rr=[]
    for dd in cal:
        names=hold.get(dd,[]); n=len(names)
        if n==0: rr.append(0.0); continue
        r=np.nanmean(ret.loc[dd,names].values); w=1.0/n
        c=w*buy*len([t for t in entd.get(dd,[]) if t in names])+w*sell*len([t for t in extd.get(dd,[]) if t in names])
        rr.append((0.0 if np.isnan(r) else r)-c)
    return pd.Series(rr,index=cal)
ihr=ihs.reindex(cal).pct_change().fillna(0)
msk=pd.DatetimeIndex(cal).year!=2025
def cagr(s): 
    eq=(1+s).cumprod(); return 100*(eq.iloc[-1]**(252/len(s))-1)
print("%-34s %9s %9s"%("","full","ex-2025"))
for nm,(b,s) in [("GROSS (zero cost)",(0,0)),
                 ("NET at repo costs 0.25/0.35",(0.0025,0.0035)),
                 ("NET at 2x repo costs",(0.005,0.007))]:
    S=curve(b,s); e=S-ihr
    print("%-34s %8.2f%% %8.2f%%"%(nm+" — excess CAGR",cagr(e),cagr(e[msk])))
S0=curve(0,0); S1=curve(0.0025,0.0035)
print("\ncost drag = %.2f%%/yr (full), %.2f%%/yr (ex-2025)"%(cagr(S0-ihr)-cagr(S1-ihr),cagr((S0-ihr)[msk])-cagr((S1-ihr)[msk])))
print("turnover: %.1f entries+exits per day, mean %.0f positions -> %.1f round trips per slot per yr"%(
    (len(P)*2)/len(cal), np.mean([len(v) for v in hold.values()]), 252*(len(P)/len(cal))/np.mean([len(v) for v in hold.values()])))
