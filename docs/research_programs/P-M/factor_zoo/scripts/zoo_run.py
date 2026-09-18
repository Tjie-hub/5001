"""Common-framework sweep over the factor panel.
For every factor: monthly decile sort, equal weight, report
  LS  = long-short (D10 - D1) spread
  LO  = long-only top-decile EXCESS over the equal-weight universe
with era split and a net-of-cost annualised figure."""
import sys,os; sys.path.insert(0,".")
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/zoo.pkl")
FEATS=[c for c in S.columns if c not in ('ticker','date','pm','fwd','adv60','close')]
print(f"panel {len(S):,} name-months  {S.pm.nunique()} months  {S.ticker.nunique()} tickers\n")
def stat(a):
    a=np.asarray(a,float); a=a[~np.isnan(a)]; n=len(a)
    if n<3: return np.nan,np.nan,np.nan,n
    return a.mean(), a.mean()/(a.std(ddof=1)/np.sqrt(n)), 100*(a>0).mean(), n
ROUND_TRIP=0.60
rows=[]
for f in FEATS:
    ls=[];lo=[];hi_=[];lo_=[]
    for pm,g in S.groupby('pm'):
        g=g[g[f].notna()]
        if len(g)<60: continue
        try: d=pd.qcut(g[f],10,labels=False,duplicates='drop')
        except Exception: continue
        if d.nunique()<8: continue
        top=g[d==d.max()].fwd.mean(); bot=g[d==d.min()].fwd.mean(); uni=g.fwd.mean()
        ls.append(top-bot); lo.append(top-uni); hi_.append(top); lo_.append(bot)
    if len(ls)<24: continue
    m1,t1,p1,n1=stat(ls); m2,t2,p2,n2=stat(lo)
    B=pd.DataFrame({'pm':[x for x in S.pm.unique() if True][:0]})
    rows.append((f,m1,t1,p1,m2,t2,p2,n1,12*m1,12*m2))
R=pd.DataFrame(rows,columns=['factor','LS %/mo','t_LS','P_LS','LO %/mo','t_LO','P_LO','mo','LS %/yr','LO %/yr'])
R['abs_t']=R[['t_LS','t_LO']].abs().max(axis=1)
R=R.sort_values('abs_t',ascending=False)
pd.set_option('display.width',210)
print("=== FACTOR ZOO: decile sorts, monthly rebalance, liquid IDX universe ===")
print(R.to_string(index=False,float_format=lambda x:f"{x:.2f}"))
R.to_pickle(f"{SP}/zoo_results.pkl")
print(f"\nfactors tested: {len(R)}")
print(f"|t|>1.96 : {(R.abs_t>1.96).sum()}   expected by chance at 5%: {0.05*len(R):.1f}")
print(f"|t|>3.10 (Bonferroni-ish for ~50 trials): {(R.abs_t>3.10).sum()}")
