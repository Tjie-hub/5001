"""Build one panel carrying every signal that survived any screen, so a
composite can be formed. Signals are cross-sectionally z-scored each month
(rank-based, robust to the fat tails that wrecked the mean-based tests)."""
import sys,os; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/trade_panel.pkl")
Z=pd.read_pickle(f"{SP}/zoo.pkl")[['ticker','date','hi52','mom12_1','ma200']]
CF=pd.read_pickle(f"{SP}/fund_cashflow.pkl").rename(columns={'Free Cash Flow':'fcf'})
SH=pd.read_pickle(f"{SP}/fund_shares.pkl")
FU=pd.read_pickle(f"{SP}/fund_annual.pkl")
with connect(read_only=True) as c:
    CA=pd.read_sql("SELECT ticker,date,value FROM corporate_actions WHERE action='dividend'",c)
for d,cc in ((S,'date'),(Z,'date'),(SH,'date'),(CF,'period_end'),(FU,'period_end'),(CA,'date')):
    d[cc]=pd.to_datetime(d[cc]).astype('datetime64[ns]')
S=S.merge(Z,on=['ticker','date'],how='left')
CF['avail']=CF.period_end+pd.DateOffset(months=6); FU['avail']=FU.period_end+pd.DateOffset(months=6)
FU['book']=FU['Stockholders Equity']
S=pd.merge_asof(S.sort_values('date'),CF.sort_values('avail')[['ticker','avail','fcf']],left_on='date',right_on='avail',by='ticker')
S=pd.merge_asof(S.sort_values('date'),FU.sort_values('avail')[['ticker','avail','book','Net Income']].rename(columns={'Net Income':'ni'}),
                left_on='date',right_on='avail',by='ticker',suffixes=('','_fu'))
S=pd.merge_asof(S.sort_values('date'),SH.rename(columns={'date':'sd'}).sort_values('sd'),left_on='date',right_on='sd',by='ticker',allow_exact_matches=False)
S['mcap']=S.shares*S.close
S['fcfp']=S.fcf/S.mcap
CAg={t:g.sort_values('date') for t,g in CA.groupby('ticker')}
rows=[]
for t,g in S.groupby('ticker'):
    cg=CAg.get(t)
    if cg is None: rows.append(pd.Series(0.0,index=g.index)); continue
    d=g.date.values; dd=cg.date.values; vv=cg.value.values; out=np.zeros(len(g))
    for i,x in enumerate(d):
        out[i]=vv[(dd<x)&(dd>=x-np.timedelta64(365,'D'))].sum()
    rows.append(pd.Series(out,index=g.index))
S['divyield']=100*pd.concat(rows).sort_index()/S.close
S['lowvol']=-S.park60                      # sign so that HIGH = good everywhere
S=S.replace([np.inf,-np.inf],np.nan)
SIG=['divyield','lowvol','hi52','fcfp']
for f in SIG:
    S['z_'+f]=S.groupby('pm',group_keys=False)[f].transform(
        lambda s: (s.rank(pct=True)-0.5)*2 if s.notna().sum()>=30 else np.nan)
S.to_pickle(f"{SP}/composite.pkl")
C=S[S.clean]
print(f"panel {len(S):,}  clean {len(C):,}  months {S.pm.nunique()}")
print("\nsignal coverage on clean panel and pairwise rank correlation:")
for f in SIG: print(f"  {f:10} {100*C['z_'+f].notna().mean():5.1f}%")
print()
print(C[['z_'+f for f in SIG]].corr(method='spearman').round(3).to_string())
