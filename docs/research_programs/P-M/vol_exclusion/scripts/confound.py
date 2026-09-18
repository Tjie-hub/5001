import sys; sys.path.insert(0,"."); sys.path.insert(0,__import__("os").path.dirname(__file__))
from base import *
df=panel(); S=snapshots(df)
print(f"snapshots: {len(S)} name-months, {S.pm.nunique()} months\n")

print("=== 1. Is high Parkinson-vol the same thing as low price? ===")
for pm,g in [(None,S)]:
    print(f"  corr(park60, log price)      = {np.corrcoef(g.park60,np.log(g.close))[0,1]:+.3f}")
    print(f"  corr(park60, log adv60)      = {np.corrcoef(g.park60,np.log(g.adv60))[0,1]:+.3f}")
d=S.groupby(S.groupby('pm').park60.transform(lambda s:pd.qcut(s,10,labels=False,duplicates='drop')))
print("\n  vol decile -> median price, median ADV, fwd return")
for k,g in d:
    print(f"   D{int(k)+1:2}  px Rp {g.close.median():7,.0f}   ADV Rp {g.adv60.median()/1e9:6.2f}bn   fwd {g.fwd_m.mean():+6.2f}%")

def overlay(S,rankcol,frac=0.10,invert=False):
    """drop the top (or bottom) `frac` by rankcol each month; return incremental vs full book"""
    out=[]
    for pm,g in S.groupby('pm'):
        if len(g)<50: continue
        q=g[rankcol].quantile(1-frac if not invert else frac)
        kept=g[g[rankcol]<q] if not invert else g[g[rankcol]>q]
        if len(kept)<20: continue
        out.append(kept.fwd_m.mean()-g.fwd_m.mean())
    return stat(out)

print("\n=== 2. What does each single-variable exclusion earn? (drop top decile) ===")
rows=[]
for lab,col,inv in [("Parkinson-60 vol",'park60',False),
                    ("close-to-close vol60",'cc60',False),
                    ("LOW PRICE (drop cheapest decile)",'close',True),
                    ("LOW ADV (drop thinnest decile)",'adv60',True)]:
    m,t,p,n=overlay(S,col,0.10,inv)
    rows.append((lab,m,t,p,n))
print(pd.DataFrame(rows,columns=['overlay','incr %/mo','t','P(>0)%','months'])
      .to_string(index=False,float_format=lambda x:f"{x:.3f}"))
