import sys,os; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
exec(open(f"{SP}/divyield.py").read().split("C=S[S.clean]")[0])   # rebuild dps12/divyield
SH=pd.read_pickle(f"{SP}/fund_shares.pkl"); SH['date']=pd.to_datetime(SH.date).astype('datetime64[ns]')
S=pd.merge_asof(S.sort_values('date'),SH.rename(columns={'date':'sd'}).sort_values('sd'),
                left_on='date',right_on='sd',by='ticker',allow_exact_matches=False)
S['mcap']=S.shares*S.close; S['size']=np.log(S.mcap.where(S.mcap>0))
C=S[S.clean].copy()
def stat(a):
    a=np.asarray(a,float);a=a[~np.isnan(a)];n=len(a)
    if n<3: return np.nan,np.nan,np.nan,n
    return a.mean(),a.mean()/(a.std(ddof=1)/np.sqrt(n)),100*(a>0).mean(),n
print("=== is dividend yield just a SIZE or LIQUIDITY proxy? ===")
sub=C[C.divyield.notna()&C['size'].notna()]
print(f"  corr(divyield, log mcap) = {sub.divyield.corr(sub['size']):+.3f}")
print(f"  corr(divyield, log adv)  = {sub.divyield.corr(np.log(sub.adv60)):+.3f}")
print(f"  corr(divyield, park60)   = {sub.divyield.corr(sub.park60):+.3f}")
print("\n  double sort: yield within size terciles (median excess, CLEAN)")
for k,lab in [(2,'LARGE'),(1,'MID'),(0,'SMALL')]:
    out=[]
    for pm,g in C.groupby('pm'):
        g=g[g.fwd.notna()&g['size'].notna()]
        if len(g)<60: continue
        g=g.assign(st=pd.qcut(g['size'],3,labels=False,duplicates='drop'))
        gg=g[g.st==k]
        if len(gg)<20: continue
        H=gg[gg.divyield>=gg.divyield.quantile(0.80)]
        if len(H)<5: continue
        out.append(H.fwd.median()-gg.fwd.median())
    m,t,p,n=stat(out)
    print(f"    {lab:6} median excess {m:+.2f}%/mo  t={t:5.2f}  P>0={p:3.0f}%  n={n}")
print("\n=== PORTFOLIO: chained month-end, tradeable prices, 0.60% round trip ===")
with connect(read_only=True) as c:
    o=pd.read_sql("SELECT ticker,date,close FROM ohlcv WHERE is_final=1 AND volume>0",c)
o['date']=pd.to_datetime(o.date); px=o.pivot_table(index='date',columns='ticker',values='close')
def book(label,sel_fn,minn=10):
    holds=[]
    for pm,g in C.groupby('pm'):
        g=g[g.fwd.notna()]
        if len(g)<50: continue
        s=sel_fn(g)
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
    yrs=(B.d1.iloc[-1]-B.d0.iloc[0]).days/365.25
    B['yr']=B.d0.dt.year; ex=B[B.yr!=2025]; ye=(ex.d1.iloc[-1]-ex.d0.iloc[0]).days/365.25
    eq=(1+B.net/100).cumprod()
    t=B.net.mean()/(B.net.std(ddof=1)/np.sqrt(len(B)))
    print(f"  {label:42} n={B.n.mean():4.0f} turn={B.turn.mean():.2f} "
          f"NET {100*((1+B.net/100).prod()**(1/yrs)-1):+7.2f}%/yr (t {t:5.2f})  "
          f"EX25 {100*((1+ex.net/100).prod()**(1/ye)-1):+7.2f}%  maxDD {100*(eq/eq.cummax()-1).min():6.1f}%")
    return B
book("top-20% yield",                 lambda g: g[g.divyield>=g.divyield.quantile(0.80)])
book("top-20% yield + vol-exclusion",  lambda g: g[(g.divyield>=g.divyield.quantile(0.80))&(g.park60<g.park60.quantile(0.90))])
book("all payers + vol-exclusion",     lambda g: g[g.paysdiv&(g.park60<g.park60.quantile(0.90))],minn=30)
book("vol-exclusion only (reference)", lambda g: g[g.park60<g.park60.quantile(0.90)],minn=30)
print("\n  hurdle: deposit 6.25%/yr")
