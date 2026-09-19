import sys,os; sys.path.insert(0,".")
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/ext_panel.pkl"); S['yr']=S.pm.astype(str).str[:4].astype(int)
def stat(a):
    a=np.asarray(a,float);a=a[~np.isnan(a)];n=len(a)
    if n<3: return np.nan,np.nan,np.nan,n
    return a.mean(),a.mean()/(a.std(ddof=1)/np.sqrt(n)),100*(a>0).mean(),n
def overlay(sub,neutral=False,minn=50,frac=0.10):
    out=[]
    for pm,g in sub.groupby('pm'):
        g=g[g.park60.notna()&g.fwd.notna()]
        if len(g)<minn: continue
        if neutral:
            keep=[]
            for s,gg in g.groupby('sector'):
                if len(gg)<10: keep.append(gg); continue
                keep.append(gg[gg.park60<gg.park60.quantile(1-frac)])
            k=pd.concat(keep)
        else:
            k=g[g.park60<g.park60.quantile(1-frac)]
        if len(k)<20: continue
        out.append(k.fwd.mean()-g.fwd.mean())
    return stat(out)
C=S[S.clean]
print("=== VOLATILITY OVERLAY on 26 years (clean, tradeability-conditioned) ===")
print(f"{'window':22} {'pooled':>9} {'t':>6} | {'sector-neutral':>15} {'t':>6} | {'mo':>4}")
wins=[("FULL 2000-2026",C),("2010-2026",C[C.yr>=2010]),("2013-2026",C[C.yr>=2013]),
      ("PRE-2021 ONLY",C[C.yr<2021]),("2010-2020 (unseen)",C[(C.yr>=2010)&(C.yr<2021)]),
      ("2021-2026 (known)",C[C.yr>=2021])]
for lab,sub in wins:
    a=overlay(sub); b=overlay(sub,neutral=True)
    print(f"{lab:22} {a[0]:9.3f} {a[1]:6.2f} | {b[0]:15.3f} {b[1]:6.2f} | {a[3]:4}")
print("\n=== by 5-year block (pooled) ===")
for lo in [2000,2005,2010,2015,2020,2025]:
    sub=C[(C.yr>=lo)&(C.yr<lo+5)]
    m,t,p,n=overlay(sub)
    if n>=10: print(f"  {lo}-{lo+4}  incr {m:+.3f}%/mo  t={t:5.2f}  P>0={p:3.0f}%  n={n:3}  names/mo {sub.groupby('pm').size().mean():4.0f}")
print("\n=== DIVIDEND YIELD on the extended panel ===")
def dy(sub,neutral=False,frac=0.20,minn=50):
    out=[]
    for pm,g in sub.groupby('pm'):
        g=g[g.divyield.notna()&g.fwd.notna()]
        if len(g)<minn: continue
        g=g[g.park60<g.park60.quantile(0.90)]
        if neutral:
            keep=[]
            for s,gg in g.groupby('sector'):
                if len(gg)<8: continue
                keep.append(gg[gg.divyield>=gg.divyield.quantile(1-frac)])
            if not keep: continue
            sel=pd.concat(keep)
        else:
            sel=g[g.divyield>=g.divyield.quantile(1-frac)]
        if len(sel)<10: continue
        out.append(sel.fwd.mean()-g.fwd.mean())
    return stat(out)
print(f"{'window':22} {'pooled':>9} {'t':>6} | {'sector-neutral':>15} {'t':>6} | {'mo':>4}")
for lab,sub in wins:
    a=dy(sub); b=dy(sub,neutral=True)
    print(f"{lab:22} {a[0]:9.3f} {a[1]:6.2f} | {b[0]:15.3f} {b[1]:6.2f} | {a[3]:4}")
