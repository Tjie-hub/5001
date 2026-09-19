import sys,os; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/trade_panel.pkl")
CF=pd.read_pickle(f"{SP}/fund_cashflow.pkl"); SH=pd.read_pickle(f"{SP}/fund_shares.pkl")
with connect(read_only=True) as c:
    CA=pd.read_sql("SELECT ticker,date,value FROM corporate_actions WHERE action='dividend'",c)
    o=pd.read_sql("SELECT ticker,date,close FROM ohlcv WHERE is_final=1 AND volume>0",c)
for d,cc in ((S,'date'),(SH,'date'),(CF,'period_end'),(CA,'date'),(o,'date')):
    d[cc]=pd.to_datetime(d[cc]).astype('datetime64[ns]')
CF['avail']=CF.period_end+pd.DateOffset(months=6)
CF=CF.rename(columns={'Free Cash Flow':'fcf'})
S=pd.merge_asof(S.sort_values('date'),CF.sort_values('avail')[['ticker','avail','fcf']],left_on='date',right_on='avail',by='ticker')
S=pd.merge_asof(S.sort_values('date'),SH.rename(columns={'date':'sd'}).sort_values('sd'),left_on='date',right_on='sd',by='ticker',allow_exact_matches=False)
S['mcap']=S.shares*S.close; S['fcfp']=S.fcf/S.mcap
CAg={t:g.sort_values('date') for t,g in CA.groupby('ticker')}
rows=[]
for t,g in S.groupby('ticker'):
    cg=CAg.get(t)
    if cg is None: rows.append(pd.Series(0.0,index=g.index)); continue
    d=g.date.values; dd=cg.date.values; vv=cg.value.values; out=np.zeros(len(g))
    for i,x in enumerate(d):
        m=(dd<x)&(dd>=x-np.timedelta64(365,'D')); out[i]=vv[m].sum()
    rows.append(pd.Series(out,index=g.index))
S['dps12']=pd.concat(rows).sort_index(); S['divyield']=100*S.dps12/S.close
S=S.replace([np.inf,-np.inf],np.nan); C=S[S.clean].copy()
sub=C[C.fcfp.notna()&C.divyield.notna()]
print(f"=== are FCF/P and dividend yield the same signal? ===")
print(f"  corr = {sub.fcfp.corr(sub.divyield):+.3f}  (rank {sub.fcfp.corr(sub.divyield,method='spearman'):+.3f})")
ov=[]
for pm,g in sub.groupby('pm'):
    if len(g)<50: continue
    a=set(g[g.fcfp>=g.fcfp.quantile(0.8)].ticker); b=set(g[g.divyield>=g.divyield.quantile(0.8)].ticker)
    if a: ov.append(len(a&b)/len(a))
print(f"  top-quintile overlap: {100*np.mean(ov):.1f}%")
px=o.pivot_table(index='date',columns='ticker',values='close')
def book(label,fn,minn=10):
    holds=[]
    for pm,g in C.groupby('pm'):
        g=g[g.fwd.notna()]
        if len(g)<50: continue
        s=fn(g)
        if len(s)<minn: continue
        holds.append((g.date.max(),list(s.ticker)))
    holds.sort(); rows=[];prev=set()
    for i in range(len(holds)-1):
        d0,nm=holds[i]; d1=holds[i+1][0]
        if d0 not in px.index or d1 not in px.index: continue
        p0=px.loc[d0,nm]; p1=px.loc[d1,nm]; ok=p0.notna()&p1.notna()
        if ok.sum()<8: continue
        r=100*((p1[ok]/p0[ok]).mean()-1)
        cur=set(np.array(nm)[ok.values]); to=len(cur-prev)/len(cur) if prev else 1.0; prev=cur
        rows.append((d0,d1,r-to*0.60,ok.sum(),to))
    B=pd.DataFrame(rows,columns=['d0','d1','net','n','turn'])
    if len(B)<12: print(f"  {label:44} too few periods"); return
    yrs=(B.d1.iloc[-1]-B.d0.iloc[0]).days/365.25; B['yr']=B.d0.dt.year
    ex=B[B.yr!=2025]; ye=(ex.d1.iloc[-1]-ex.d0.iloc[0]).days/365.25
    eq=(1+B.net/100).cumprod(); t=B.net.mean()/(B.net.std(ddof=1)/np.sqrt(len(B)))
    print(f"  {label:44} n={B.n.mean():4.0f} NET {100*((1+B.net/100).prod()**(1/yrs)-1):+7.2f}%/yr (t {t:5.2f})"
          f"  EX25 {100*((1+ex.net/100).prod()**(1/ye)-1):+7.2f}%  maxDD {100*(eq/eq.cummax()-1).min():6.1f}%  per={len(B)}")
print("\n=== PORTFOLIOS (chained, tradeable prices, 0.60% round trip) ===")
V=lambda g: g.park60<g.park60.quantile(0.90)
book("dividend top-20% + volex",       lambda g: g[(g.divyield>=g.divyield.quantile(0.8))&V(g)])
book("FCF/P top-20% + volex",          lambda g: g[(g.fcfp>=g.fcfp.quantile(0.8))&V(g)])
book("EITHER high-yield or high-FCF/P",lambda g: g[((g.divyield>=g.divyield.quantile(0.8))|(g.fcfp>=g.fcfp.quantile(0.8)))&V(g)],minn=20)
book("BOTH high-yield and high-FCF/P", lambda g: g[(g.divyield>=g.divyield.quantile(0.8))&(g.fcfp>=g.fcfp.quantile(0.8))&V(g)],minn=6)
print("\n  hurdle: deposit 6.25%/yr")
