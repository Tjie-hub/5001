import sys,os; sys.path.insert(0,"."); sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from base import *
df=panel(); S=snapshots(df)

def overlay(S,col,frac):
    out=[]
    for pm,g in S.groupby('pm'):
        if len(g)<50: continue
        q=g[col].quantile(1-frac); kept=g[g[col]<q]
        if len(kept)<20: continue
        out.append(kept.fwd_m.mean()-g.fwd_m.mean())
    return stat(out)

print("=== 3. EXCLUSION FRACTION sweep (Parkinson-60) ===")
rows=[(f"{int(f*100)}%",)+overlay(S,'park60',f) for f in [0.02,0.05,0.10,0.15,0.20,0.30,0.40]]
print(pd.DataFrame(rows,columns=['drop','incr %/mo','t','P(>0)%','mo']).to_string(index=False,float_format=lambda x:f"{x:.3f}"))

print("\n=== 4. ESTIMATOR sweep (drop top decile) ===")
g0=df.groupby('ticker',group_keys=False)
for w in [20,40,120]:
    hl=np.log(df.high/df.low)**2
    p=hl.groupby(df.ticker).transform(lambda s:s.rolling(w,min_periods=w).mean())
    df[f'park{w}']=np.sqrt(p/(4*np.log(2)))*np.sqrt(252)*100
df['dn60']=g0.close.transform(lambda s:s.pct_change().clip(upper=0).rolling(60,min_periods=60).std())*np.sqrt(252)*100
S2=snapshots(df)
rows=[]
for col in ['park20','park40','park60','park120','cc60','dn60']:
    if col not in S2.columns: continue
    s=S2[S2[col].notna()]
    rows.append((col,)+overlay(s,col,0.10))
print(pd.DataFrame(rows,columns=['estimator','incr %/mo','t','P(>0)%','mo']).to_string(index=False,float_format=lambda x:f"{x:.3f}"))

print("\n=== 5. Is it just BETA reduction? (regress book excess on benchmark) ===")
rows=[]
for pm,g in S.groupby('pm'):
    if len(g)<50: continue
    q=g.park60.quantile(0.90); kept=g[g.park60<q]
    if len(kept)<20: continue
    rows.append((pm.to_timestamp(),kept.fwd_m.mean(),g.fwd_m.mean()))
B=pd.DataFrame(rows,columns=['m','book','bench'])
x=B.bench.values; y=B.book.values
beta,alpha=np.polyfit(x,y,1)
res=y-(alpha+beta*x); se=res.std(ddof=2)/np.sqrt(len(x))/1  # alpha SE
sa=np.sqrt(((res**2).sum()/(len(x)-2))*(1/len(x)+x.mean()**2/((x-x.mean())**2).sum()))
print(f"  beta = {beta:.3f}   alpha = {alpha:+.3f}%/mo   t(alpha) = {alpha/sa:.2f}   n={len(x)} months")
print(f"  -> beta near 1.0 means the gain is NOT merely de-risking" if beta>0.9 else "  -> beta well below 1: much of the gain is de-risking")
