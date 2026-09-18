import sys,os; sys.path.insert(0,".")
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP="/tmp/claude-1000/-home-tjiesar-10-Projects-idx-walkforward-5001/eae2ba9d-2aa0-44ee-b5dd-9ad732c34cb2/scratchpad"
S=pd.read_pickle(f"{SP}/zoo.pkl"); S['yr']=S.pm.astype(str).str[:4]
RT=0.60
def book(frac=0.10,volex=False,minn=10):
    rows=[];prev=set()
    for pm,g in S.groupby('pm'):
        g=g[g.hi52.notna()]
        if len(g)<60: continue
        if volex: g=g[g.park60<g.park60.quantile(0.90)]
        q=g.hi52.quantile(1-frac); sel=g[g.hi52>=q]
        if len(sel)<minn: continue
        names=set(sel.ticker); to=len(names-prev)/len(names) if prev else 1.0; prev=names
        rows.append((pm,str(pm)[:4],sel.fwd.mean(),sel.fwd.median(),g.fwd.mean(),to,len(sel)))
    B=pd.DataFrame(rows,columns=['pm','yr','ret','med','uni','turn','n'])
    B['cost']=B.turn*RT
    B['net']=B.ret-B.cost
    return B
def rep(lab,B):
    n=len(B); ann=lambda s:((1+s/100).prod())**(12/n)-1
    sh=(B.net.mean()/B.net.std())*np.sqrt(12)
    eq=(1+B.net/100).cumprod(); dd=(eq/eq.cummax()-1).min()
    t=B.net.mean()/(B.net.std(ddof=1)/np.sqrt(n))
    print(f"{lab:34} n={B.n.mean():5.0f} turn={B.turn.mean():.2f} "
          f"GROSS {100*ann(B.ret):+6.2f}%/yr  NET {100*ann(B.net):+6.2f}%/yr  "
          f"Sharpe {sh:5.2f}  maxDD {100*dd:6.1f}%  t={t:4.2f}")
    return B
print("=== 52-WEEK-HIGH BOOK: absolute net performance ===")
print(f"(universe equal-weight benchmark and IHSG shown at the end; hurdle is 6-7%/yr)\n")
for frac,lab in [(0.05,'top 5%'),(0.10,'top 10%'),(0.20,'top 20%'),(0.30,'top 30%')]:
    rep(f"hi52 {lab}",book(frac))
print()
for frac,lab in [(0.10,'top 10%'),(0.20,'top 20%'),(0.30,'top 30%')]:
    rep(f"hi52 {lab} + vol-exclusion",book(frac,volex=True))
B=book(0.20)
print(f"\n  benchmark (equal-wt universe)   {100*(((1+B.uni/100).prod())**(12/len(B))-1):+6.2f}%/yr")
print(f"  by year (net, top 20%):")
Bv=book(0.20,volex=True)
for y in sorted(B.yr.unique()):
    a=B[B.yr==y]; b=Bv[Bv.yr==y]
    print(f"    {y}  hi52 {100*(((1+a.net/100).prod())-1):+7.2f}%   +volex {100*(((1+b.net/100).prod())-1):+7.2f}%"
          f"   universe {100*(((1+a.uni/100).prod())-1):+7.2f}%")
