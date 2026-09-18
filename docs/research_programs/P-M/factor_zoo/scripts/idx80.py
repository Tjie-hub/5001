"""IDX80-only test, using POINT-IN-TIME membership from idx80_membership_history.
Membership is joined by effective_from/effective_to so no name is ever in the
book before it was actually a constituent."""
import sys,os; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/zoo_fund.pkl"); S['yr']=S.pm.astype(str).str[:4]
with connect(read_only=True) as c:
    M=pd.read_sql("SELECT ticker,period_label,effective_from,effective_to FROM idx80_membership_history WHERE membership_status='MEMBER'",c)
M['effective_from']=pd.to_datetime(M.effective_from)
M['effective_to']=pd.to_datetime(M.effective_to).fillna(pd.Timestamp('2099-12-31'))
S['date']=pd.to_datetime(S.date)
print(f"IDX80 membership: {M.period_label.nunique()} periods, {M.effective_from.min().date()} -> onward")
# point-in-time membership flag
S['idx80']=False
for _,r in M.iterrows():
    m=(S.ticker==r.ticker)&(S.date>=r.effective_from)&(S.date<=r.effective_to)
    S.loc[m,'idx80']=True
cov=S[S.date>=M.effective_from.min()]
print(f"panel months overlapping IDX80 data: {cov.pm.nunique()} of {S.pm.nunique()}")
print(f"IDX80 names per month (in panel): {cov[cov.idx80].groupby('pm').size().mean():.0f} of 80")
print(f"  (gap = IDX80 members failing the ADV>=Rp1bn / px>=Rp50 panel filter, or not priced)\n")
RT=0.60
def ann(s,n): return 100*(((1+s/100).prod())**(12/n)-1)
def run(label,sub,sort='hi52',frac=0.20,volex=True,minn=8):
    rows=[];prev=set()
    for pm,g in sub.groupby('pm'):
        g=g[g[sort].notna()&g.fwd.notna()]
        if len(g)<20: continue
        if volex and g.park60.notna().sum()>10: g=g[g.park60<g.park60.quantile(0.90)]
        q=g[sort].quantile(1-frac); sel=g[g[sort]>=q]
        if len(sel)<minn: continue
        nm=set(sel.ticker); to=len(nm-prev)/len(nm) if prev else 1.0; prev=nm
        rows.append((str(pm)[:4],sel.fwd.mean(),g.fwd.mean(),to,len(sel)))
    B=pd.DataFrame(rows,columns=['yr','ret','uni','turn','n'])
    if len(B)<10: print(f"  {label:44} too few periods ({len(B)})"); return
    B['net']=B.ret-B.turn*RT; n=len(B)
    t=B.net.mean()/(B.net.std(ddof=1)/np.sqrt(n))
    print(f"  {label:44} periods={n:3} names={B.n.mean():4.0f}  NET {ann(B.net,n):+7.2f}%/yr (t {t:5.2f})"
          f"  universe {ann(B.uni,n):+7.2f}%/yr")
W=S[S.date>=M.effective_from.min()]          # same window for both
print("=== SAME WINDOW (2025-01 onward), IDX80 vs broad universe ===")
run("IDX80 only : hi52 top20 + volex",W[W.idx80])
run("broad      : hi52 top20 + volex",W)
print()
def volex_only(label,sub):
    rows=[]
    for pm,g in sub.groupby('pm'):
        g=g[g.park60.notna()&g.fwd.notna()]
        if len(g)<20: continue
        k=g[g.park60<g.park60.quantile(0.90)]
        rows.append((k.fwd.mean()-g.fwd.mean(),))
    a=np.array([r[0] for r in rows])
    if len(a)<10: print(f"  {label:44} too few"); return
    t=a.mean()/(a.std(ddof=1)/np.sqrt(len(a)))
    print(f"  {label:44} periods={len(a):3}  incr {a.mean():+.3f}%/mo (t {t:5.2f})  {12*a.mean():+.2f}%/yr")
print("=== vol-exclusion overlay, same window ===")
volex_only("IDX80 only",W[W.idx80]); volex_only("broad universe",W)

print("\n=== is the IDX80 failure BREADTH or the SIGNAL? widen the book ===")
for frac,lab in [(0.20,'top 20% (~15 names)'),(0.35,'top 35% (~26)'),(0.50,'top 50% (~38)'),(0.75,'top 75% (~57)')]:
    run(f"IDX80 hi52 {lab}",W[W.idx80],frac=frac,minn=6)
print("\n=== where does the edge live? IDX80 vs the rest of the liquid universe ===")
run("NON-IDX80 liquid : hi52 top20 + volex",W[~W.idx80])
volex_only("NON-IDX80 liquid : vol-exclusion only",W[~W.idx80])
print("\n=== universe returns over the same 19 periods (mean, equal weight) ===")
for lab,sub in [('IDX80',W[W.idx80]),('non-IDX80 liquid',W[~W.idx80]),('all liquid',W)]:
    r=sub.groupby('pm').fwd.mean()
    print(f"  {lab:20} mean {r.mean():+6.2f}%/mo   median {sub.fwd.median():+6.2f}%   names/mo {sub.groupby('pm').size().mean():5.0f}")
