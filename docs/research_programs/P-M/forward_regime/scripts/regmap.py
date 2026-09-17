import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
exec(open(os.environ['SP']+'/bullrank.py').read().split("rows=[]")[0])   # reuse panel + P definitions
def diff_vs_base(s,b):
    x=np.r_[(s.fo20-COST).values,(b.fo20-COST).values]
    gg=np.r_[np.ones(len(s)),np.zeros(len(b))]; dt=np.r_[s.date.values,b.date.values]
    X=np.c_[np.ones(len(x)),gg]; beta=np.linalg.lstsq(X,x,rcond=None)[0]; e=x-X@beta
    XtXi=np.linalg.inv(X.T@X); meat=np.zeros((2,2))
    for k in pd.unique(dt):
        m_=dt==k; xs=X[m_]; es=e[m_]; sc=xs.T@es; meat+=np.outer(sc,sc)
    V=XtXi@meat@XtXi
    return beta[1]*100, beta[1]/np.sqrt(V[1,1])
print("=== SCREENING PER REGIME: what each pattern ADDS over that regime's own baseline ===")
for rg in ['BULL','SIDEWAYS','BEAR']:
    b=d[d.liq&(d.rg==rg)&d.fo20.notna()&(d.bad20.fillna(1)==0)]
    base=((b.fo20-COST)*100).mean()
    print(f"\n--- {rg}  (baseline: random liquid stock = {base:+.2f}% net/20d, N={len(b)}) ---")
    rows=[]
    for nm,m in P.items():
        mm=(m&d.liq&(d.rg==rg)).fillna(False)
        s=d[mm&d.fo20.notna()&(d.bad20.fillna(1)==0)]
        if len(s)<40: rows.append((nm,len(s),np.nan,np.nan,np.nan,np.nan)); continue
        net=((s.fo20-COST)*100).mean()
        dd,t=diff_vs_base(s,b)
        # era stability inside the cell
        s2=s.copy(); s2['yr']=s2.date.dt.year
        yrs=s2.groupby('yr').apply(lambda g:((g.fo20-COST)*100).mean()-base if len(g)>=10 else np.nan)
        pos=int((yrs.dropna()>0).sum()); tot=int(yrs.notna().sum())
        rows.append((nm,len(s),net,dd,t,f"{pos}/{tot}"))
    R=pd.DataFrame(rows,columns=['strategy','N','net20%','ADDS%','t','yrs +ve'])
    print(R.sort_values('ADDS%',ascending=False).to_string(index=False,float_format=lambda x:f"{x:.2f}"))

print("\n\n=== RECONCILIATION: 'in UP state' vs 'episode ONSET' (what spec 002 actually trades) ===")
up=(d.sl_1>0.02)&(d.er_1>=0.30)&(d.pa_1>=0.70)
prev=d.groupby('ticker',sort=False).apply(lambda x:((x.sl_1>0.02)&(x.er_1>=0.30)&(x.pa_1>=0.70)).shift(1),include_groups=False).reset_index(level=0,drop=True)
onset=(up & ~prev.fillna(False).astype(bool))
for rg in ['BULL','SIDEWAYS','BEAR']:
    b=d[d.liq&(d.rg==rg)&d.fo20.notna()&(d.bad20.fillna(1)==0)]
    base=((b.fo20-COST)*100).mean()
    r=[]
    for lbl,m in [('any UP day',up),('ONSET only (spec 002)',onset)]:
        mm=(m&d.liq&(d.rg==rg)).fillna(False)
        s=d[mm&d.fo20.notna()&(d.bad20.fillna(1)==0)]
        if len(s)<30: r.append((lbl,0,np.nan,np.nan)); continue
        net=((s.fo20-COST)*100).mean()
        dd,t=diff_vs_base(s,b)
        r.append((lbl,len(s),net,dd))
    print(f"  {rg:9s} baseline {base:+6.2f}%  |  " + "  |  ".join(
        f"{lbl}: N={n:5d} net {net:+6.2f}% adds {dd:+6.2f}%" for lbl,n,net,dd in r))
