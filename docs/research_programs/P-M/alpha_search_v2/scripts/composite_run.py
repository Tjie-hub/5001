import sys,os; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/composite.pkl"); C=S[S.clean].copy()
with connect(read_only=True) as c:
    o=pd.read_sql("SELECT ticker,date,close FROM ohlcv WHERE is_final=1 AND volume>0",c)
o['date']=pd.to_datetime(o.date); px=o.pivot_table(index='date',columns='ticker',values='close')
def comp(g,sigs):
    cols=['z_'+f for f in sigs]
    return g[cols].mean(axis=1,skipna=True)
def book(label,sigs,frac=0.20,hold=1,minn=15,require=None):
    holds=[]
    for pm,g in C.groupby('pm'):
        g=g[g.fwd.notna()].copy()
        if len(g)<50: continue
        g['sc']=comp(g,sigs)
        if require: g=g[g[['z_'+f for f in require]].notna().all(axis=1)]
        g=g[g.sc.notna()]
        if len(g)<40: continue
        sel=g[g.sc>=g.sc.quantile(1-frac)]
        if len(sel)<minn: continue
        holds.append((g.date.max(),list(sel.ticker)))
    holds.sort()
    rows=[];prev=set()
    for i in range(0,len(holds)-hold,hold):
        d0,nm=holds[i]; d1=holds[i+hold][0]
        if d0 not in px.index or d1 not in px.index: continue
        p0=px.loc[d0,nm]; p1=px.loc[d1,nm]; ok=p0.notna()&p1.notna()
        if ok.sum()<10: continue
        r=100*((p1[ok]/p0[ok]).mean()-1)
        cur=set(np.array(nm)[ok.values]); to=len(cur-prev)/len(cur) if prev else 1.0; prev=cur
        rows.append((d0,d1,r-to*0.60,ok.sum(),to))
    B=pd.DataFrame(rows,columns=['d0','d1','net','n','turn'])
    if len(B)<10: print(f"  {label:46} too few periods ({len(B)})"); return None
    yrs=(B.d1.iloc[-1]-B.d0.iloc[0]).days/365.25; B['yr']=B.d0.dt.year
    ex=B[B.yr!=2025]; ye=(ex.d1.iloc[-1]-ex.d0.iloc[0]).days/365.25 if len(ex)>2 else np.nan
    eq=(1+B.net/100).cumprod(); t=B.net.mean()/(B.net.std(ddof=1)/np.sqrt(len(B)))
    per_yr=len(B)/yrs
    sh=B.net.mean()/B.net.std()*np.sqrt(per_yr)
    exn=100*((1+ex.net/100).prod()**(1/ye)-1) if len(ex)>2 else np.nan
    print(f"  {label:46} n={B.n.mean():4.0f} NET {100*((1+B.net/100).prod()**(1/yrs)-1):+7.2f}%/yr "
          f"(t {t:5.2f}) EX25 {exn:+7.2f}%  Sh {sh:5.2f}  DD {100*(eq/eq.cummax()-1).min():6.1f}%  per={len(B)}")
    return B
print("=== COMPOSITE BOOKS, monthly, top 20%, 0.60% round trip ===")
book("divyield only (reference)",      ['divyield'])
book("lowvol only (reference)",        ['lowvol'])
book("divyield + lowvol",              ['divyield','lowvol'])
book("divyield + lowvol + hi52",       ['divyield','lowvol','hi52'])
book("all four",                       ['divyield','lowvol','hi52','fcfp'])
print("\n=== concentration sweep on the best 2-signal composite ===")
for f in [0.10,0.20,0.30,0.40]:
    book(f"divyield+lowvol top {int(f*100)}%",['divyield','lowvol'],frac=f)
print("\n=== holding period (dividend yield is slow-moving; does patience pay?) ===")
for h in [1,3,6]:
    book(f"divyield+lowvol, hold {h}m",['divyield','lowvol'],hold=h)
