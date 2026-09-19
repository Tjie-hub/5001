import sys,os; sys.path.insert(0,".")
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/trade_panel.pkl")
FU=pd.read_pickle(f"{SP}/fund_annual.pkl"); SH=pd.read_pickle(f"{SP}/fund_shares.pkl")
for d,c in ((S,'date'),(SH,'date'),(FU,'period_end')): d[c]=pd.to_datetime(d[c]).astype('datetime64[ns]')
FU['avail']=FU.period_end+pd.DateOffset(months=6)
FU['noa']=FU['Total Assets']-FU['Cash And Cash Equivalents']
FU['rnoa']=FU['Operating Income']/FU.noa.where(FU.noa>0)
FU['rnoa_ebit']=FU['EBIT']/FU.noa.where(FU.noa>0)
FU['oaturn']=FU['Total Revenue']/FU.noa.where(FU.noa>0)
FU['opmargin']=FU['Operating Income']/FU['Total Revenue'].where(FU['Total Revenue']>0)
S=pd.merge_asof(S.sort_values('date'),FU.sort_values('avail')[['ticker','avail','rnoa','rnoa_ebit','oaturn','opmargin','noa']],
                left_on='date',right_on='avail',by='ticker')
S=pd.merge_asof(S.sort_values('date'),SH.rename(columns={'date':'sd'}).sort_values('sd'),
                left_on='date',right_on='sd',by='ticker',allow_exact_matches=False)
S['mcap']=S.shares*S.close
S=S.replace([np.inf,-np.inf],np.nan)
C=S[S.clean]
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
print("=== #4 RNOA and operating-profitability decomposition (IDX4 paper's factor) ===")
print(f"{'factor':12} {'cover%':>7} | {'TOP mean':>9} {'t':>6} | {'TOP median':>11} {'t':>6}")
for col in ['rnoa','rnoa_ebit','oaturn','opmargin']:
    h,hm=sweep(col,C)
    print(f"{col:12} {100*C[col].notna().mean():6.1f}% | {h[0]:9.2f} {h[1]:6.2f} | {hm[0]:11.2f} {hm[1]:6.2f}")

print("\n=== CALENDAR EFFECTS (documented on IDX; heavily data-mined historically) ===")
C2=C.copy(); C2['mo']=C2.pm.astype(str).str[5:7]
print("  month-of-year: mean forward 1-month return of the equal-weight liquid universe")
rows=[]
for m,g in C2.groupby('mo'):
    r=g.groupby('pm').fwd.mean()
    mm,t,p,n=stat(r.values)
    rows.append((m,mm,t,p,n))
R=pd.DataFrame(rows,columns=['month','mean%','t','P>0','n'])
print(R.to_string(index=False,float_format=lambda x:f"{x:.2f}"))
jan=R[R.month=='01']; rest=R[R.month!='01']
print(f"\n  January mean {jan['mean%'].iloc[0]:+.2f}%  vs other months {rest['mean%'].mean():+.2f}%")
print(f"  (n={jan['n'].iloc[0]} Januaries -- far too few for inference; reported for completeness only)")
