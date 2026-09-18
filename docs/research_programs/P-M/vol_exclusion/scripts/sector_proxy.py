import sys,os; sys.path.insert(0,"."); sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from base import *
df=panel(); S=snapshots(df)
df['ret']=df.groupby('ticker',group_keys=False).close.transform(lambda s:s.pct_change())
R=df.pivot_table(index='date',columns='ticker',values='ret')

rng=np.random.default_rng(3)
rows=[]
for pm,g in S.groupby('pm'):
    if len(g)<80: continue
    end=g.date.max()
    win=R.loc[:end].tail(60)
    q=g.park60.quantile(0.90)
    exc=[t for t in g[g.park60>=q].ticker if t in win.columns]
    uni=[t for t in g.ticker if t in win.columns]
    if len(exc)<8 or len(uni)<60: continue
    def avgcorr(names):
        M=win[names].dropna(axis=1,thresh=40)
        if M.shape[1]<5: return np.nan,np.nan
        C=M.corr().values
        iu=np.triu_indices_from(C,1)
        v=C[iu]; v=v[~np.isnan(v)]
        # PC1 share
        X=M.fillna(0).values; X=X-X.mean(0)
        try:
            s=np.linalg.svd(X,compute_uv=False); pc1=s[0]**2/(s**2).sum()
        except Exception: pc1=np.nan
        return (np.nanmean(v),pc1)
    ce,pe=avgcorr(exc)
    ctrl=[];pctrl=[]
    for _ in range(30):
        samp=list(rng.choice(uni,len(exc),replace=False))
        a,b=avgcorr(samp); ctrl.append(a); pctrl.append(b)
    rows.append((pm,len(exc),ce,np.nanmean(ctrl),pe,np.nanmean(pctrl)))
D=pd.DataFrame(rows,columns=['pm','n_exc','corr_exc','corr_rand','pc1_exc','pc1_rand'])
print(f"months tested: {len(D)}\n")
print("=== 15. Is the excluded decile a concentrated (sector-like) bet? ===")
print(f"  mean pairwise corr  excluded {D.corr_exc.mean():.4f}   random same-size {D.corr_rand.mean():.4f}"
      f"   diff {D.corr_exc.mean()-D.corr_rand.mean():+.4f}")
d=(D.corr_exc-D.corr_rand).values; m,t,p,n=stat(d)
print(f"  paired diff: {m:+.4f}  t={t:.2f}  P(>0)={p:.0f}%  n={n}")
print(f"  PC1 variance share  excluded {D.pc1_exc.mean():.3f}   random {D.pc1_rand.mean():.3f}"
      f"   diff {D.pc1_exc.mean()-D.pc1_rand.mean():+.3f}")
d2=(D.pc1_exc-D.pc1_rand).values; m2,t2,p2,_=stat(d2)
print(f"  paired diff: {m2:+.4f}  t={t2:.2f}  P(>0)={p2:.0f}%")
print("\n  interpretation: if excluded names were a sector bet, their pairwise correlation")
print("  and PC1 share would be MATERIALLY above a random same-size basket.")

print("\n=== 16. Name persistence in the excluded decile ===")
prev=None; ov=[]
allnames={}
for pm,g in S.groupby('pm'):
    if len(g)<80: continue
    q=g.park60.quantile(0.90); cur=set(g[g.park60>=q].ticker)
    for t in cur: allnames[t]=allnames.get(t,0)+1
    if prev: ov.append(len(cur&prev)/len(cur))
    prev=cur
print(f"  month-to-month overlap of the excluded set: {100*np.mean(ov):.1f}%")
c=pd.Series(allnames).sort_values(ascending=False)
print(f"  distinct names ever excluded: {len(c)}   (universe ~{S.ticker.nunique()})")
print(f"  names excluded in >=50% of months: {(c>=0.5*len(ov)).sum()}")
print(f"  top recurrers: {', '.join(f'{k}({v})' for k,v in c.head(8).items())}")
