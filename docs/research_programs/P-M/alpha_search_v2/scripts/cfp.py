"""Cash-flow-to-price and free-cash-flow-to-price -- the EM literature's
strongest value measures, and the IDX4 model's value factor.
6-month publication lag, long-only, tradeability-conditioned panel."""
import sys,os; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/trade_panel.pkl")
CF=pd.read_pickle(f"{SP}/fund_cashflow.pkl")
SH=pd.read_pickle(f"{SP}/fund_shares.pkl")
FU=pd.read_pickle(f"{SP}/fund_annual.pkl")
for d,c in ((S,'date'),(SH,'date'),(CF,'period_end'),(FU,'period_end')):
    d[c]=pd.to_datetime(d[c]).astype('datetime64[ns]')
print("cashflow fields available:")
for c in CF.columns:
    if c in ('ticker','period_end'): continue
    print(f"  {c:46} {100*CF[c].notna().mean():5.1f}%")
CF['avail']=CF.period_end+pd.DateOffset(months=6)
CF=CF.rename(columns={'Operating Cash Flow':'ocf','Capital Expenditure':'capex','Free Cash Flow':'fcf'})
if 'fcf' not in CF.columns: CF['fcf']=np.nan
CF['fcf']=CF.fcf.fillna(CF.ocf+CF.get('capex',0))
FU['avail']=FU.period_end+pd.DateOffset(months=6)
S=pd.merge_asof(S.sort_values('date'),CF.sort_values('avail')[['ticker','avail','ocf','fcf']],
                left_on='date',right_on='avail',by='ticker')
S=pd.merge_asof(S.sort_values('date'),SH.rename(columns={'date':'sd'}).sort_values('sd'),
                left_on='date',right_on='sd',by='ticker',allow_exact_matches=False)
S['mcap']=S.shares*S.close
S['cfp']=S.ocf/S.mcap
S['fcfp']=S.fcf/S.mcap
S=S.replace([np.inf,-np.inf],np.nan)
C=S[S.clean]
print(f"\ncoverage on clean panel: cfp {100*C.cfp.notna().mean():.1f}%  fcfp {100*C.fcfp.notna().mean():.1f}%")
def stat(a):
    a=np.asarray(a,float);a=a[~np.isnan(a)];n=len(a)
    if n<3: return np.nan,np.nan,np.nan,n
    return a.mean(),a.mean()/(a.std(ddof=1)/np.sqrt(n)),100*(a>0).mean(),n
def sweep(col,sub,frac=0.20):
    hi,him=[],[]
    for pm,g in sub.groupby('pm'):
        g=g[g[col].notna()&g.fwd.notna()]
        if len(g)<50: continue
        H=g[g[col]>=g[col].quantile(1-frac)]
        if len(H)<8: continue
        hi.append(H.fwd.mean()-g.fwd.mean()); him.append(H.fwd.median()-g.fwd.median())
    return stat(hi),stat(him)
print("\n=== #3 CASH-FLOW-TO-PRICE (long-only, top 20%) ===")
print(f"{'factor':8} | {'mean':>7} {'t':>6} | {'median':>8} {'t':>6} | {'n':>4}")
for col in ['cfp','fcfp']:
    h,hm=sweep(col,C)
    print(f"{col:8} | {h[0]:7.2f} {h[1]:6.2f} | {hm[0]:8.2f} {hm[1]:6.2f} | {h[3]:4}")
print("\n  era split:")
for col in ['cfp','fcfp']:
    for lab,sub in [("2021-23",C[C.pm.astype(str).str[:4]<='2023']),("2024-26",C[C.pm.astype(str).str[:4]>='2024']),
                    ("EX-2025",C[C.pm.astype(str).str[:4]!='2025'])]:
        h,hm=sweep(col,sub)
        print(f"    {col:5} {lab:8} mean {h[0]:+6.2f} (t {h[1]:5.2f})  median {hm[0]:+6.2f} (t {hm[1]:5.2f})  n={h[3]}")
print("\n=== does CF/P add to dividend yield? (are they the same thing?) ===")
sub=C[C.cfp.notna()]
print(f"  corr(cfp, divyield) unavailable here -- rebuilt separately; corr(cfp, log mcap) = {sub.cfp.corr(np.log(sub.mcap)):+.3f}")
