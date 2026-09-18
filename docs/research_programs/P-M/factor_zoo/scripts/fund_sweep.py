import sys,os; sys.path.insert(0,".")
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/zoo_fund.pkl"); S['yr']=S.pm.astype(str).str[:4]
FF=['size','btm','roe','earn_yield','sales_p','gp_assets','leverage','ag','op_assets']
def stat(a):
    a=np.asarray(a,float);a=a[~np.isnan(a)];n=len(a)
    if n<3: return np.nan,np.nan,np.nan,n
    return a.mean(),a.mean()/(a.std(ddof=1)/np.sqrt(n)),100*(a>0).mean(),n
def sweep(f,frac=0.10):
    mt,md,names=[],[],[]
    for pm,g in S.groupby('pm'):
        g=g[g[f].notna()&g.fwd.notna()]
        if len(g)<50: continue
        hq=g[f].quantile(1-frac); lq=g[f].quantile(frac)
        hi=g[g[f]>=hq]; lo=g[g[f]<=lq]
        if len(hi)<5 or len(lo)<5: continue
        mt.append((hi.fwd.mean()-g.fwd.mean(), lo.fwd.mean()-g.fwd.mean(),
                   hi.fwd.median()-g.fwd.median(), lo.fwd.median()-g.fwd.median()))
    if len(mt)<24: return None
    A=np.array(mt)
    return dict(n=len(A),
        hi_m=stat(A[:,0]),lo_m=stat(A[:,1]),hi_md=stat(A[:,2]),lo_md=stat(A[:,3]))
print(f"panel with fundamentals: {S.btm.notna().sum():,} name-months, {S.pm.nunique()} months\n")
print("=== FUNDAMENTAL FACTORS: top/bottom decile excess over equal-wt universe ===")
print(f"{'factor':11} {'n':>4} | {'TOP mean':>9} {'t':>6} {'TOP med':>8} {'t':>6} | {'BOT mean':>9} {'t':>6} {'BOT med':>8} {'t':>6}")
res={}
for f in FF:
    r=sweep(f)
    if not r: print(f"{f:11} insufficient"); continue
    res[f]=r
    print(f"{f:11} {r['n']:4} | {r['hi_m'][0]:9.2f} {r['hi_m'][1]:6.2f} {r['hi_md'][0]:8.2f} {r['hi_md'][1]:6.2f} "
          f"| {r['lo_m'][0]:9.2f} {r['lo_m'][1]:6.2f} {r['lo_md'][0]:8.2f} {r['lo_md'][1]:6.2f}")
print("\n  a factor is only interesting if the MEDIAN column agrees with the MEAN column.")
print("\n=== ERA SPLIT for anything with |median t| > 2 ===")
for f in FF:
    if f not in res: continue
    for side,key in (('top','hi_md'),('bot','lo_md')):
        if abs(res[f][key][1])<2: continue
        rows=[]
        for pm,g in S.groupby('pm'):
            g=g[g[f].notna()&g.fwd.notna()]
            if len(g)<50: continue
            q=g[f].quantile(0.90 if side=='top' else 0.10)
            s=g[g[f]>=q] if side=='top' else g[g[f]<=q]
            if len(s)<5: continue
            rows.append((str(pm)[:4],s.fwd.median()-g.fwd.median()))
        B=pd.DataFrame(rows,columns=['yr','x'])
        e1=stat(B[B.yr<='2023'].x); e2=stat(B[B.yr>='2024'].x); ex=stat(B[B.yr!='2025'].x)
        print(f"  {f:11} {side:4}  21-23 {e1[0]:+6.2f} (t {e1[1]:5.2f})   24-26 {e2[0]:+6.2f} (t {e2[1]:5.2f})"
              f"   EX-2025 {ex[0]:+6.2f} (t {ex[1]:5.2f})")
