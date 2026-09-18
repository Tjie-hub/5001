import sys,os; sys.path.insert(0,"."); sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from base import *
df=panel(); S=snapshots(df)
# pre-split into numpy per month (fast)
months=[]
for pm,g in S.groupby('pm'):
    if len(g)<50: continue
    months.append((pm,g.park60.values.astype(float),g.fwd_m.values.astype(float),g.ticker.values))
print(f"months usable: {len(months)}")

def incr_from(v,f,frac=0.10):
    q=np.quantile(v,1-frac); k=f[v<q]
    return (k.mean()-f.mean()) if len(k)>=5 else np.nan

print("\n=== 9. BREADTH: bootstrap annualised IR by book size ===")
rng=np.random.default_rng(11)
rows=[]
for N in [10,25,50,100,200,300]:
    irs=[]
    for b in range(120):
        out=[]
        for pm,v,f,tk in months:
            n=len(v)
            if n<max(40,N//2): continue
            idx=rng.choice(n,min(N,n),replace=False)
            x=incr_from(v[idx],f[idx])
            if not np.isnan(x): out.append(x)
        a=np.array(out)
        if len(a)>12 and a.std(ddof=1)>0:
            irs.append(a.mean()/a.std(ddof=1)*np.sqrt(12))
    rows.append((N,np.mean(irs),np.percentile(irs,25),np.percentile(irs,75),100*np.mean(np.array(irs)>0)))
print(pd.DataFrame(rows,columns=['book N','ann IR','p25','p75','% IR>0'])
      .to_string(index=False,float_format=lambda x:f"{x:.2f}"))

print("\n=== 10. DRAWDOWN / path of the overlay ===")
rows=[]
for pm,v,f,tk in months:
    q=np.quantile(v,0.90); k=f[v<q]
    rows.append((pm.to_timestamp(),k.mean()-f.mean(),k.mean(),f.mean()))
B=pd.DataFrame(rows,columns=['m','incr','book','bench']).sort_values('m').reset_index(drop=True)
cum=(1+B.incr/100).cumprod(); dd=cum/cum.cummax()-1
print(f"  cumulative overlay gain, {len(B)} months : {100*(cum.iloc[-1]-1):+.2f}%")
print(f"  worst overlay drawdown                  : {100*dd.min():.2f}%  ({B.m[dd.idxmin()].date()})")
run=mx=0
for x in B.incr:
    run=run+1 if x<0 else 0; mx=max(mx,run)
print(f"  longest run of negative months          : {mx}")
bk=(1+B.book/100).cumprod(); bn=(1+B.bench/100).cumprod()
print(f"  book CAGR {100*(bk.iloc[-1]**(12/len(B))-1):+.2f}%/yr  vs benchmark {100*(bn.iloc[-1]**(12/len(B))-1):+.2f}%/yr")
print(f"  book maxDD {100*(bk/bk.cummax()-1).min():.1f}%  vs benchmark maxDD {100*(bn/bn.cummax()-1).min():.1f}%")

print("\n=== 11. DOWN vs UP market asymmetry ===")
for lab,m in [("benchmark DOWN months",B.bench<0),("benchmark UP months",B.bench>=0)]:
    s=B[m].incr.values; mm,t,p,n=stat(s)
    print(f"  {lab:22} n={n:3}  incr {mm:+.3f}%/mo  t={t:5.2f}  P(>0)={p:.0f}%")
B.to_pickle(f"{os.path.dirname(os.path.abspath(__file__))}/overlay_series.pkl")
