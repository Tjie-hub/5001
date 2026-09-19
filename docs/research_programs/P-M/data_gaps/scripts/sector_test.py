"""GAP 1 PAYOFF: the sector confound, previously untestable with labels.
Earlier it was addressed only indirectly, via co-movement (excluded names were
LESS correlated than random, t -12.41). Now it can be tested directly."""
import sys,os; sys.path.insert(0,".")
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/composite.pkl")
SEC=pd.read_pickle(f"{SP}/sector_map.pkl")
S=S.merge(SEC[['ticker','sector','industry']],on='ticker',how='left')
C=S[S.clean&S.sector.notna()].copy()
print(f"clean name-months with a sector label: {len(C):,} ({100*len(C)/len(S[S.clean]):.1f}%)")
def stat(a):
    a=np.asarray(a,float);a=a[~np.isnan(a)];n=len(a)
    if n<3: return np.nan,np.nan,np.nan,n
    return a.mean(),a.mean()/(a.std(ddof=1)/np.sqrt(n)),100*(a>0).mean(),n
print("\n=== 1. Is the EXCLUDED (high-vol) decile a sector bet? ===")
ex=[]
for pm,g in C.groupby('pm'):
    if len(g)<50: continue
    ex.append(g[g.park60>=g.park60.quantile(0.90)])
E=pd.concat(ex)
a=E.sector.value_counts(normalize=True)*100; b=C.sector.value_counts(normalize=True)*100
cmp=pd.DataFrame({'excluded %':a,'universe %':b}).dropna(); cmp['tilt']=cmp['excluded %']-cmp['universe %']
print(cmp.sort_values('tilt',ascending=False).to_string(float_format=lambda x:f"{x:.1f}"))
hhi_e=((a/100)**2).sum(); hhi_u=((b/100)**2).sum()
print(f"\n  sector HHI: excluded {hhi_e:.3f}  universe {hhi_u:.3f}  (higher = more concentrated)")
print("\n=== 2. Does the overlay survive SECTOR-NEUTRAL construction? ===")
def overlay(sub,neutral):
    out=[]
    for pm,g in sub.groupby('pm'):
        g=g[g.park60.notna()&g.fwd.notna()]
        if len(g)<50: continue
        if neutral:
            keep=[]
            for s,gg in g.groupby('sector'):
                if len(gg)<10: keep.append(gg); continue
                keep.append(gg[gg.park60<gg.park60.quantile(0.90)])   # exclude WITHIN sector
            k=pd.concat(keep)
        else:
            k=g[g.park60<g.park60.quantile(0.90)]
        if len(k)<20: continue
        out.append(k.fwd.mean()-g.fwd.mean())
    return stat(out)
for lab,neu in [("pooled exclusion (as published)",False),("SECTOR-NEUTRAL exclusion",True)]:
    m,t,p,n=overlay(C,neu)
    print(f"  {lab:34} incr {m:+.3f}%/mo  t={t:5.2f}  P>0={p:3.0f}%  ->{12*m:+6.2f}%/yr")
print("\n=== 3. Does DIVIDEND YIELD survive sector-neutral construction? ===")
def dy(sub,neutral,frac=0.20):
    out=[]
    for pm,g in sub.groupby('pm'):
        g=g[g.divyield.notna()&g.fwd.notna()]
        if len(g)<50: continue
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
for lab,neu in [("pooled (as published)",False),("SECTOR-NEUTRAL",True)]:
    m,t,p,n=dy(C,neu)
    print(f"  {lab:34} excess {m:+.3f}%/mo  t={t:5.2f}  P>0={p:3.0f}%  ->{12*m:+6.2f}%/yr")
print("\n=== 4. Is there a SECTOR factor of its own? (top vs bottom sector by prior 12m) ===")
out=[]
for pm,g in C.groupby('pm'):
    g=g[g.fwd.notna()&g.mom12_1.notna()]
    if len(g)<60 or g.sector.nunique()<6: continue
    sm=g.groupby('sector').mom12_1.mean()
    hi=sm.idxmax(); lo=sm.idxmin()
    a=g[g.sector==hi].fwd.mean(); b=g[g.sector==lo].fwd.mean()
    out.append(a-b)
m,t,p,n=stat(out)
print(f"  sector momentum (top-sector minus bottom-sector): {m:+.2f}%/mo  t={t:5.2f}  P>0={p:.0f}%  n={n}")
