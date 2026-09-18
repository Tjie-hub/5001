"""Does adding fundamentals to the best price/volume book get us to 6-7%/yr NET?
Benchmark to beat: 6.25% deposit. Prior best was hi52-top20 + vol-exclusion:
+13.67%/yr all-era (t 1.44) but only +2.08%/yr ex-2025."""
import sys,os; sys.path.insert(0,".")
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/zoo_fund.pkl"); S['yr']=S.pm.astype(str).str[:4]
RT=0.60
def ann(s,n): return 100*(((1+s/100).prod())**(12/n)-1)
def run(label,screen,frac=0.20,sort='hi52',volex=True):
    rows=[];prev=set()
    for pm,g in S.groupby('pm'):
        g=g[g[sort].notna()&g.fwd.notna()]
        if len(g)<50: continue
        if volex and g.park60.notna().any(): g=g[g.park60<g.park60.quantile(0.90)]
        g=screen(g)
        if len(g)<25: continue
        q=g[sort].quantile(1-frac); sel=g[g[sort]>=q]
        if len(sel)<8: continue
        nm=set(sel.ticker); to=len(nm-prev)/len(nm) if prev else 1.0; prev=nm
        rows.append((str(pm)[:4],sel.fwd.mean(),sel.fwd.median(),g.fwd.mean(),to,len(sel)))
    B=pd.DataFrame(rows,columns=['yr','ret','med','uni','turn','n'])
    if len(B)<24: print(f"{label:38} insufficient"); return
    B['net']=B.ret-B.turn*RT
    n=len(B); t=B.net.mean()/(B.net.std(ddof=1)/np.sqrt(n))
    e=B[B.yr!='2025']; ne=len(e)
    te=e.net.mean()/(e.net.std(ddof=1)/np.sqrt(ne))
    sh=B.net.mean()/B.net.std()*np.sqrt(12)
    print(f"{label:38} n={B.n.mean():4.0f} ALL {ann(B.net,n):+7.2f}%/yr (t {t:5.2f}) "
          f"EX25 {ann(e.net,ne):+7.2f}%/yr (t {te:5.2f})  Sharpe {sh:5.2f}")
ok=lambda g:g
print("=== baseline (price/volume only) ===")
run("hi52 top20 + volex",ok)
print("\n=== + fundamental screens ===")
run("  & btm above median",      lambda g:g[g.btm>=g.btm.median()] if g.btm.notna().sum()>30 else g.iloc[:0])
run("  & btm top half + roe>0",  lambda g:g[(g.btm>=g.btm.median())&(g.roe>0)] if g.btm.notna().sum()>30 else g.iloc[:0])
run("  & roe above median",      lambda g:g[g.roe>=g.roe.median()] if g.roe.notna().sum()>30 else g.iloc[:0])
run("  & gp/assets above median",lambda g:g[g.gp_assets>=g.gp_assets.median()] if g.gp_assets.notna().sum()>30 else g.iloc[:0])
run("  & asset growth below med",lambda g:g[g.ag<=g.ag.median()] if g.ag.notna().sum()>30 else g.iloc[:0])
run("  & size above median",     lambda g:g[g['size']>=g['size'].median()] if g['size'].notna().sum()>30 else g.iloc[:0])
run("  & size below median",     lambda g:g[g['size']<=g['size'].median()] if g['size'].notna().sum()>30 else g.iloc[:0])
run("  & earn_yield above med",  lambda g:g[g.earn_yield>=g.earn_yield.median()] if g.earn_yield.notna().sum()>30 else g.iloc[:0])
print("\n=== fundamental-only books (no hi52) ===")
for f in ['btm','roe','gp_assets','earn_yield']:
    run(f"{f} top20 + volex",ok,sort=f)
