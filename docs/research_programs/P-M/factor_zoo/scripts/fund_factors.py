"""Build point-in-time fundamental factors and merge onto the monthly panel.

POINT-IN-TIME RULE. IDX requires audited annual reports within 90 days of
year-end, so FY(Y) is public by ~31 March of Y+1. This uses a deliberately
conservative 6-month lag: FY(Y) becomes usable only from 1 July of Y+1. Using
period-end dates directly would be look-ahead and would manufacture a value
factor out of thin air.

KNOWN LIMITATION, stated here rather than buried: Yahoo serves RESTATED
financials, not point-in-time originals. A company that restated FY2022 in 2024
shows the restated figure. This biases toward the restated (usually cleaner)
number and cannot be corrected without a vendor PIT database.
"""
import sys,os; sys.path.insert(0,".")
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/zoo.pkl")
SH=pd.read_pickle(f"{SP}/fund_shares.pkl")
FU=pd.read_pickle(f"{SP}/fund_annual.pkl")
print(f"panel {len(S):,} | shares {len(SH):,} | annual {len(FU):,}")
# normalise datetime resolution across sources (yfinance returns ns/us, DB gives s)
for _d,_c in ((S,'date'),(SH,'date'),(FU,'period_end')):
    _d[_c]=pd.to_datetime(_d[_c]).astype('datetime64[ns]')

# ---- shares outstanding as of each formation date (last obs strictly before) ----
SH=SH.sort_values(['ticker','date'])
S=S.sort_values('date')
S=pd.merge_asof(S, SH.rename(columns={'date':'sdate'}).sort_values('sdate'),
                left_on='date', right_on='sdate', by='ticker', allow_exact_matches=False)
S['mcap']=S.shares*S.close
print(f"  shares matched: {100*S.shares.notna().mean():.1f}% of name-months")

# ---- annual fundamentals with a 6-month publication lag ----
FU=FU.copy()
FU['avail']=FU.period_end + pd.DateOffset(months=6)
eq_cols=['Stockholders Equity','Total Equity Gross Minority Interest','Common Stock Equity']
FU['book']=FU[[c for c in eq_cols if c in FU.columns]].bfill(axis=1).iloc[:,0] if any(c in FU.columns for c in eq_cols) else np.nan
ni_cols=['Net Income','Net Income Common Stockholders']
FU['ni']=FU[[c for c in ni_cols if c in FU.columns]].bfill(axis=1).iloc[:,0] if any(c in FU.columns for c in ni_cols) else np.nan
for src,dst in [('Total Assets','assets'),('Total Revenue','revenue'),
                ('Gross Profit','gp'),('Total Debt','debt'),('Operating Income','opinc')]:
    FU[dst]=FU[src] if src in FU.columns else np.nan
FU=FU.sort_values(['ticker','avail'])
prev=FU.groupby('ticker').assets.shift(1)
FU['asset_growth']=(FU.assets/prev-1)
keep=['ticker','avail','period_end','book','ni','assets','revenue','gp','debt','opinc','asset_growth']
FU=FU[keep].dropna(subset=['avail'])
S=pd.merge_asof(S.sort_values('date'), FU.sort_values('avail'),
                left_on='date', right_on='avail', by='ticker', allow_exact_matches=True)
print(f"  fundamentals matched: {100*S.book.notna().mean():.1f}% of name-months")
S['stale_days']=(S.date-S.period_end).dt.days

# ---- factors ----
S['size']      = np.log(S.mcap.where(S.mcap>0))
S['btm']       = S.book/S.mcap
S['roe']       = S.ni/S.book.where(S.book>0)
S['earn_yield']= S.ni/S.mcap
S['sales_p']   = S.revenue/S.mcap
S['gp_assets'] = S.gp/S.assets.where(S.assets>0)
S['leverage']  = S.debt/S.assets.where(S.assets>0)
S['ag']        = S.asset_growth
S['op_assets'] = S.opinc/S.assets.where(S.assets>0)
FF=['size','btm','roe','earn_yield','sales_p','gp_assets','leverage','ag','op_assets']
for f in FF:
    S[f]=S[f].replace([np.inf,-np.inf],np.nan)
print("\ncoverage of the new factors (% of name-months):")
for f in FF: print(f"  {f:12} {100*S[f].notna().mean():5.1f}%")
print(f"\nstale_days (age of the fundamental at use): median {S.stale_days.median():.0f}  p90 {S.stale_days.quantile(.9):.0f}")
S.to_pickle(f"{SP}/zoo_fund.pkl")
print(f"saved zoo_fund.pkl  {len(S):,} rows")
