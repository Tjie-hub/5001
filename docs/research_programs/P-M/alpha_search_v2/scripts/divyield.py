"""Dividend yield on the tradeability-conditioned panel. Trailing 12m cash
dividends / price, using only ex-dates strictly BEFORE the formation date."""
import sys,os; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/trade_panel.pkl")
with connect(read_only=True) as c:
    CA=pd.read_sql("SELECT ticker,date,action,value FROM corporate_actions WHERE action='dividend'",c)
CA['date']=pd.to_datetime(CA.date).astype('datetime64[ns]')
S['date']=pd.to_datetime(S.date).astype('datetime64[ns]')
print(f"dividends {len(CA):,} over {CA.ticker.nunique()} tickers; value stats: "
      f"median {CA.value.median():.1f} p95 {CA.value.quantile(.95):.1f}")
# trailing 12m dividend per share, strictly prior ex-dates
rows=[]
CAg={t:g.sort_values('date') for t,g in CA.groupby('ticker')}
for t,g in S.groupby('ticker'):
    cg=CAg.get(t)
    if cg is None:
        rows.append(pd.Series(0.0,index=g.index)); continue
    d=g.date.values; out=np.zeros(len(g))
    dd=cg.date.values; vv=cg.value.values
    for i,x in enumerate(d):
        m=(dd<x)&(dd>=x-np.timedelta64(365,'D'))
        out[i]=vv[m].sum()
    rows.append(pd.Series(out,index=g.index))
S['dps12']=pd.concat(rows).sort_index()
S['divyield']=100*S.dps12/S.close
S['paysdiv']=S.dps12>0
C=S[S.clean]
print(f"  names paying a dividend in the trailing 12m: {100*C.paysdiv.mean():.1f}% of name-months")
print(f"  median yield among payers: {C[C.paysdiv].divyield.median():.2f}%  p90 {C[C.paysdiv].divyield.quantile(.9):.2f}%")
def stat(a):
    a=np.asarray(a,float);a=a[~np.isnan(a)];n=len(a)
    if n<3: return np.nan,np.nan,np.nan,n
    return a.mean(),a.mean()/(a.std(ddof=1)/np.sqrt(n)),100*(a>0).mean(),n
print("\n=== DIVIDEND YIELD, long-only, CLEAN panel ===")
def sweep(sub,frac=0.20):
    hi,him,pay,paym=[],[],[],[]
    for pm,g in sub.groupby('pm'):
        g=g[g.fwd.notna()]
        if len(g)<50: continue
        H=g[g.divyield>=g.divyield.quantile(1-frac)]
        if len(H)>=8:
            hi.append(H.fwd.mean()-g.fwd.mean()); him.append(H.fwd.median()-g.fwd.median())
        P=g[g.paysdiv]
        if len(P)>=8:
            pay.append(P.fwd.mean()-g.fwd.mean()); paym.append(P.fwd.median()-g.fwd.median())
    return stat(hi),stat(him),stat(pay),stat(paym)
h,hm,p,pm_=sweep(C)
print(f"  top-20% yield   mean {h[0]:+.2f}%/mo (t {h[1]:5.2f})   median {hm[0]:+.2f} (t {hm[1]:5.2f})  n={h[3]}")
print(f"  any payer       mean {p[0]:+.2f}%/mo (t {p[1]:5.2f})   median {pm_[0]:+.2f} (t {pm_[1]:5.2f})  n={p[3]}")
print("\n  era split (top-20% yield):")
for lab,sub in [("2021-23",C[C.pm.astype(str).str[:4]<='2023']),("2024-26",C[C.pm.astype(str).str[:4]>='2024']),
                ("EX-2025",C[C.pm.astype(str).str[:4]!='2025'])]:
    a,b,_,_=sweep(sub)
    print(f"    {lab:8} mean {a[0]:+.2f} (t {a[1]:5.2f})  median {b[0]:+.2f} (t {b[1]:5.2f})  n={a[3]}")
print("\n=== does dividend-paying STACK with volatility exclusion? ===")
def combo(sub,use_div,frac=0.10):
    out=[]
    for pm,g in sub.groupby('pm'):
        g=g[g.park60.notna()&g.fwd.notna()]
        if len(g)<50: continue
        k=g[g.park60<g.park60.quantile(1-frac)]
        if use_div: k=k[k.paysdiv]
        if len(k)<20: continue
        out.append(k.fwd.mean()-g.fwd.mean())
    return stat(out)
for lab,ud in [("vol exclusion only",False),("vol exclusion + payers only",True)]:
    m,t,p2,n=combo(C,ud)
    print(f"  {lab:30} incr {m:+.3f}%/mo  t={t:5.2f}  P>0={p2:3.0f}%  ->{12*m:+6.2f}%/yr")
