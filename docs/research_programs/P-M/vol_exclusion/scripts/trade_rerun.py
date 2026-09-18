import sys,os; sys.path.insert(0,".")
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/trade_panel.pkl"); S['yr']=S.pm.astype(str).str[:4]
def stat(a):
    a=np.asarray(a,float);a=a[~np.isnan(a)];n=len(a)
    if n<3: return np.nan,np.nan,np.nan,n
    return a.mean(),a.mean()/(a.std(ddof=1)/np.sqrt(n)),100*(a>0).mean(),n
def overlay(sub,col='park60',tgt='fwd',frac=0.10,minn=50):
    out=[]
    for pm,g in sub.groupby('pm'):
        g=g[g[col].notna()&g[tgt].notna()]
        if len(g)<minn: continue
        k=g[g[col]<g[col].quantile(1-frac)]
        if len(k)<20: continue
        out.append(k[tgt].mean()-g[tgt].mean())
    return stat(out)
print("=== VOLATILITY EXCLUSION OVERLAY under tradeability conditioning ===")
print(f"{'panel':46} {'incr %/mo':>10} {'t':>6} {'P>0':>5} {'n':>4} {'ann':>8}")
rows=[
 ("as published (all rows, close-to-close fwd)", S, 'fwd'),
 ("drop frz_fwd (return not earnable)",          S[~S.frz_fwd], 'fwd'),
 ("drop frz_form (vol est. contaminated)",       S[~S.frz_form], 'fwd'),
 ("drop suspension episodes",                    S[~S.susp], 'fwd'),
 ("CLEAN (none of the three)",                   S[S.clean], 'fwd'),
 ("CLEAN + tradeable-price fwd return",          S[S.clean], 'fwd_t'),
]
for lab,sub,tgt in rows:
    m,t,p,n=overlay(sub,tgt=tgt)
    print(f"{lab:46} {m:10.3f} {t:6.2f} {p:5.0f} {n:4} {12*m:+8.2f}%")
print("\n=== era split on the CLEAN panel ===")
C=S[S.clean]
for lab,sub in [("2021-2023",C[C.yr<='2023']),("2024-2026",C[C.yr>='2024']),("EX-2025",C[C.yr!='2025'])]:
    m,t,p,n=overlay(sub)
    print(f"  {lab:12} incr {m:+.3f}%/mo  t={t:5.2f}  P>0={p:3.0f}%  n={n}")
print("\n=== down/up asymmetry on the CLEAN panel ===")
rows=[]
for pm,g in C.groupby('pm'):
    g=g[g.park60.notna()&g.fwd.notna()]
    if len(g)<50: continue
    k=g[g.park60<g.park60.quantile(0.90)]
    if len(k)<20: continue
    rows.append((g.fwd.mean(),k.fwd.mean()-g.fwd.mean()))
B=pd.DataFrame(rows,columns=['uni','incr'])
for lab,m in [("benchmark DOWN",B.uni<0),("benchmark UP",B.uni>=0)]:
    mm,t,p,n=stat(B[m].incr.values)
    print(f"  {lab:16} n={n:3}  incr {mm:+.3f}%/mo  t={t:5.2f}  P>0={p:.0f}%")
print("\n=== exclusion fraction sweep, CLEAN panel ===")
for f in [0.02,0.05,0.10,0.15,0.20,0.30]:
    m,t,p,n=overlay(C,frac=f)
    print(f"  drop top {int(f*100):2}%  incr {m:+.3f}%/mo  t={t:5.2f}  P>0={p:3.0f}%")
print("\n=== what were we actually excluding? returns of the excluded decile ===")
for lab,sub in [("all rows",S),("CLEAN only",C)]:
    ex=[]
    for pm,g in sub.groupby('pm'):
        g=g[g.park60.notna()&g.fwd.notna()]
        if len(g)<50: continue
        ex.append(g[g.park60>=g.park60.quantile(0.90)].fwd.mean()-g.fwd.mean())
    m,t,p,n=stat(ex)
    print(f"  {lab:12} excluded decile excess {m:+.2f}%/mo  t={t:5.2f}  n={n}")
