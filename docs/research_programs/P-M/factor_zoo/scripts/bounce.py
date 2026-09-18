"""Decisive microstructure test. Close-to-close returns on low-priced IDX names
are inflated by bid-ask bounce (Blume-Stambaugh): the formation close is itself a
transaction price, so a stock that closed on the bid shows a spurious gain.
Re-measure every signal with entry at the NEXT OPEN and exit at the open 21
sessions later, so no formation-day price is ever a transaction price."""
import sys,os; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP="/tmp/claude-1000/-home-tjiesar-10-Projects-idx-walkforward-5001/eae2ba9d-2aa0-44ee-b5dd-9ad732c34cb2/scratchpad"
S=pd.read_pickle(f"{SP}/zoo.pkl")
with connect(read_only=True) as c:
    o=pd.read_sql("SELECT ticker,date,open,close FROM ohlcv WHERE is_final=1 AND volume>0",c)
o['date']=pd.to_datetime(o.date); o=o.sort_values(['ticker','date'])
g=o.groupby('ticker',group_keys=False)
o['nxt_open']=g.open.transform(lambda s:s.shift(-1))
o['exit_open']=g.open.transform(lambda s:s.shift(-22))
o['fwd_oo']=100*(o.exit_open/o.nxt_open-1)
S=S.merge(o[['ticker','date','fwd_oo']],on=['ticker','date'],how='left')
print(f"panel {len(S):,}  with open-to-open fwd: {S.fwd_oo.notna().sum():,} ({100*S.fwd_oo.notna().mean():.1f}%)\n")
def stat(a):
    a=np.asarray(a,float);a=a[~np.isnan(a)];n=len(a)
    if n<3: return np.nan,np.nan,np.nan,n
    return a.mean(),a.mean()/(a.std(ddof=1)/np.sqrt(n)),100*(a>0).mean(),n
def run(f,side,tgt,frac=0.10):
    out=[]
    for pm,gg in S.groupby('pm'):
        gg=gg[gg[f].notna()&gg[tgt].notna()]
        if len(gg)<60: continue
        q=gg[f].quantile(1-frac if side=='top' else frac)
        sel=gg[gg[f]>=q] if side=='top' else gg[gg[f]<=q]
        if len(sel)<6: continue
        out.append(sel[tgt].mean()-gg[tgt].mean())
    return stat(out)
CAND=[('px','bot'),('hi52','top'),('ma50','top'),('mom1','top'),('rev1w','top'),
      ('ma200','top'),('skew60','top'),('park60','excl')]
print("=== CLOSE-TO-CLOSE vs OPEN-TO-OPEN (the bounce test) ===")
print(f"{'factor':10} {'side':5} | {'C2C %/mo':>9} {'t':>6} | {'O2O %/mo':>9} {'t':>6} | {'lost':>7}")
for f,side in CAND:
    if side=='excl':
        def ex(tgt):
            out=[]
            for pm,gg in S.groupby('pm'):
                gg=gg[gg[f].notna()&gg[tgt].notna()]
                if len(gg)<60: continue
                k=gg[gg[f]<gg[f].quantile(0.90)]
                out.append(k[tgt].mean()-gg[tgt].mean())
            return stat(out)
        a=ex('fwd'); b=ex('fwd_oo')
    else:
        a=run(f,side,'fwd'); b=run(f,side,'fwd_oo')
    lost=100*(1-b[0]/a[0]) if a[0] and not np.isnan(b[0]) else np.nan
    print(f"{f:10} {side:5} | {a[0]:9.2f} {a[1]:6.2f} | {b[0]:9.2f} {b[1]:6.2f} | {lost:6.0f}%")
