import sys,os; sys.path.insert(0,"."); sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from base import *
df=panel(); S=snapshots(df)
g0=df.groupby('ticker',group_keys=False)
df['dn60']=g0.close.transform(lambda s:s.pct_change().clip(upper=0).rolling(60,min_periods=60).std())*np.sqrt(252)*100
S=snapshots(df)

def series(S,col='park60',frac=0.10):
    rows=[]
    for pm,g in S.groupby('pm'):
        if len(g)<50: continue
        q=g[col].quantile(1-frac); k=g[g[col]<q]
        if len(k)<20: continue
        rows.append((pm,k.fwd_m.mean()-g.fwd_m.mean(),k.fwd_m.mean(),g.fwd_m.mean()))
    return pd.DataFrame(rows,columns=['pm','incr','book','bench'])

print("=== 6. ERA STABILITY by estimator (drop top decile) ===")
rows=[]
for col in ['park60','cc60','dn60']:
    B=series(S,col); B['yr']=B.pm.astype(str).str[:4]
    e1=B[B.yr<='2023'].incr; e2=B[B.yr>='2024'].incr
    rows.append((col,*stat(e1)[:2],*stat(e2)[:2],
                 " ".join(f"{y}:{gg.incr.mean():+.2f}" for y,gg in B.groupby('yr'))))
print(pd.DataFrame(rows,columns=['est','21-23 %/mo','t','24-26 %/mo','t','by year'])
      .to_string(index=False,float_format=lambda x:f"{x:.3f}"))

print("\n=== 7. REBALANCE FREQUENCY (how stale can the vol rank get?) ===")
me=month_ends(df)
rows=[]
for lag in [0,1,2,3,6]:
    out=[]
    for pm,g in S.groupby('pm'):
        if len(g)<50: continue
        # use vol as of `lag` months earlier
        src=S[S.pm==(pm-lag)] if lag else g
        if len(src)<50: continue
        mp=src.set_index('ticker').park60
        gg=g.copy(); gg['v']=gg.ticker.map(mp)
        gg=gg.dropna(subset=['v'])
        if len(gg)<50: continue
        q=gg.v.quantile(0.90); k=gg[gg.v<q]
        if len(k)<20: continue
        out.append(k.fwd_m.mean()-gg.fwd_m.mean())
    m,t,p,n=stat(out)
    rows.append((f"{lag} mo stale",m,t,p,n))
print(pd.DataFrame(rows,columns=['vol rank age','incr %/mo','t','P(>0)%','mo'])
      .to_string(index=False,float_format=lambda x:f"{x:.3f}"))

print("\n=== 8. COST DEATH POINT (turnover of the overlay) ===")
B=series(S)
turn=[]
prev=None
for pm,g in S.groupby('pm'):
    if len(g)<50: continue
    q=g.park60.quantile(0.90); k=set(g[g.park60<q].ticker)
    if prev is not None and len(prev):
        turn.append(len(k^prev)/ (2*len(k)))
    prev=k
tm=np.mean(turn)
print(f"  overlay one-way turnover: {100*tm:.1f}%/mo  ({100*tm*12:.0f}%/yr)")
gross=B.incr.mean()*12
for c in [0.6,0.8,1.0,1.2,1.5,2.0]:
    drag=2*tm*12*(c/2)
    print(f"  round trip {c:.1f}%  -> annual drag {drag:.2f}%   net {gross-drag:+.2f}%/yr")
print(f"\n  gross overlay edge {gross:+.2f}%/yr; dies at round trip ~{gross/(tm*12):.2f}%")
