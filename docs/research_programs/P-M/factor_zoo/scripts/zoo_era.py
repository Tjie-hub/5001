import sys,os; sys.path.insert(0,".")
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__)); S=pd.read_pickle(f"{SP}/zoo.pkl")
S['yr']=S.pm.astype(str).str[:4]
def stat(a):
    a=np.asarray(a,float); a=a[~np.isnan(a)]; n=len(a)
    if n<3: return np.nan,np.nan,np.nan,n
    return a.mean(), a.mean()/(a.std(ddof=1)/np.sqrt(n)), 100*(a>0).mean(), n
def build(f,side='top',frac=0.10):
    rows=[]; prev=set()
    for pm,g in S.groupby('pm'):
        g=g[g[f].notna()]
        if len(g)<60: continue
        q=g[f].quantile(1-frac if side=='top' else frac)
        sel=g[g[f]>=q] if side=='top' else g[g[f]<=q]
        if len(sel)<6: continue
        names=set(sel.ticker)
        to=len(names-prev)/len(names) if prev else 1.0
        prev=names
        rows.append((pm,str(pm)[:4],sel.fwd.mean(),g.fwd.mean(),sel.fwd.mean()-g.fwd.mean(),to,len(sel)))
    return pd.DataFrame(rows,columns=['pm','yr','sel','uni','exc','turn','n'])
CAND=[('hi52','top'),('ma50','top'),('mom1','top'),('rev1w','top'),('ma200','top'),
      ('park60','bot'),('vol60','bot'),('ivol120','bot'),('px','bot'),('skew60','top')]
print("=== ERA SPLIT + NET OF COST (top/bottom decile long-only, excess over equal-wt universe) ===")
print(f"{'factor':10} {'side':5} {'exc%/mo':>8} {'t':>6} {'P>0':>5} {'21-23':>7} {'24-26':>7} {'turn':>6} {'gross%/yr':>10} {'NET%/yr':>8}")
keep={}
for f,side in CAND:
    B=build(f,side); 
    if len(B)<24: continue
    m,t,p,n=stat(B.exc)
    e1=stat(B[B.yr<='2023'].exc)[0]; e2=stat(B[B.yr>='2024'].exc)[0]
    tu=B.turn.mean(); gross=12*m; net=gross-2*tu*12*(0.60/2)
    print(f"{f:10} {side:5} {m:8.2f} {t:6.2f} {p:5.0f} {e1:7.2f} {e2:7.2f} {tu:6.2f} {gross:10.2f} {net:8.2f}")
    keep[f+"_"+side]=B.set_index('pm').exc
print("\n=== correlation among the surviving signals (are they one factor?) ===")
C=pd.DataFrame(keep).corr()
print(C.to_string(float_format=lambda x:f"{x:+.2f}"))
