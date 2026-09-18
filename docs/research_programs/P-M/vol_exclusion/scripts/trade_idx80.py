import sys,os; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/trade_panel.pkl"); S['yr']=S.pm.astype(str).str[:4]
with connect(read_only=True) as c:
    M=pd.read_sql("SELECT ticker,effective_from,effective_to FROM idx80_membership_history WHERE membership_status='MEMBER'",c)
M['effective_from']=pd.to_datetime(M.effective_from)
M['effective_to']=pd.to_datetime(M.effective_to).fillna(pd.Timestamp('2099-12-31'))
S['idx80']=False
for _,r in M.iterrows():
    S.loc[(S.ticker==r.ticker)&(S.date>=r.effective_from)&(S.date<=r.effective_to),'idx80']=True
W=S[S.date>=M.effective_from.min()]
def stat(a):
    a=np.asarray(a,float);a=a[~np.isnan(a)];n=len(a)
    if n<3: return np.nan,np.nan,np.nan,n
    return a.mean(),a.mean()/(a.std(ddof=1)/np.sqrt(n)),100*(a>0).mean(),n
def overlay(sub,minn=20):
    out=[]
    for pm,g in sub.groupby('pm'):
        g=g[g.park60.notna()&g.fwd.notna()]
        if len(g)<minn: continue
        k=g[g.park60<g.park60.quantile(0.90)]
        if len(k)<10: continue
        out.append(k.fwd.mean()-g.fwd.mean())
    return stat(out)
print("=== IDX80 re-run under tradeability conditioning (19 periods, 2025-01+) ===")
for lab,sub in [("IDX80  as published",W[W.idx80]),
                ("IDX80  CLEAN",W[W.idx80 & W.clean]),
                ("non-IDX80  as published",W[~W.idx80]),
                ("non-IDX80  CLEAN",W[~W.idx80 & W.clean]),
                ("all liquid CLEAN",W[W.clean])]:
    m,t,p,n=overlay(sub)
    print(f"  {lab:28} incr {m:+.3f}%/mo  t={t:5.2f}  P>0={p:3.0f}%  n={n}  ->{12*m:+6.2f}%/yr")
print("\n=== contamination rate by universe (why IDX80 differs) ===")
for lab,sub in [("IDX80",W[W.idx80]),("non-IDX80 liquid",W[~W.idx80])]:
    print(f"  {lab:20} frz_form {100*sub.frz_form.mean():5.2f}%  frz_fwd {100*sub.frz_fwd.mean():5.2f}%  "
          f"susp {100*sub.susp.mean():5.2f}%  clean {100*sub.clean.mean():5.2f}%")
print("\n=== full-history CLEAN overlay by universe proxy (ADV terciles, all 58 months) ===")
S['advt']=S.groupby('pm',group_keys=False).adv60.transform(lambda s:pd.qcut(s,3,labels=False,duplicates='drop'))
for k,lab in [(2,'top ADV tercile (IDX80-like)'),(1,'mid ADV tercile'),(0,'bottom ADV tercile')]:
    m,t,p,n=overlay(S[(S.advt==k)&S.clean],minn=40)
    print(f"  {lab:30} incr {m:+.3f}%/mo  t={t:5.2f}  P>0={p:3.0f}%  ->{12*m:+6.2f}%/yr")
