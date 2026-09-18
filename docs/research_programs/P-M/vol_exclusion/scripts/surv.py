import sys,os; sys.path.insert(0,"."); sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from base import *
df=panel()
END=df.date.max()
last=df.groupby('ticker').date.max()
first=df.groupby('ticker').date.min()
# a name is "dead" if it stops printing >60 sessions before corpus end
sess=sorted(df.date.unique())
cut=sess[-61]
dead=set(last[last<cut].index); alive=set(last[last>=cut].index)
print(f"=== 17. SURVIVORSHIP ===")
print(f"  corpus end {str(END)[:10]};  dead (last print before {str(cut)[:10]}): {len(dead)}  alive: {len(alive)}")

S=snapshots(df)
S['dead']=S.ticker.isin(dead)
print(f"  eligible name-months from later-dead names: {100*S.dead.mean():.2f}%")
# are dead names higher vol?
vr=S.groupby('pm',group_keys=False).park60.rank(pct=True)
S=S.assign(vrank=vr)
print(f"  mean vol percentile  dead {S[S.dead].vrank.mean():.3f}   alive {S[~S.dead].vrank.mean():.3f}")
print(f"  share of the EXCLUDED decile that is later-dead: "
      f"{100*S[S.vrank>=0.9].dead.mean():.2f}%  (vs {100*S.dead.mean():.2f}% base)")
# final-year returns of dead names
print(f"  mean fwd_m of later-dead name-months : {S[S.dead].fwd_m.mean():+.2f}%")
print(f"  mean fwd_m of surviving name-months  : {S[~S.dead].fwd_m.mean():+.2f}%")

def overlay(X,frac=0.10):
    out=[]
    for pm,g in X.groupby('pm'):
        if len(g)<50: continue
        q=g.park60.quantile(1-frac); k=g[g.park60<q]
        if len(k)<20: continue
        out.append(k.fwd_m.mean()-g.fwd_m.mean())
    return stat(out)
print("\n  overlay measured on:")
for lab,X in [("FULL panel (incl. later-dead)",S),("SURVIVORS ONLY (dead removed)",S[~S.dead])]:
    m,t,p,n=overlay(X)
    print(f"    {lab:34} incr {m:+.3f}%/mo  t={t:5.2f}  P(>0)={p:.0f}%  n={n}")
print("  => if survivors-only is WEAKER, the corpus's zero-dropout roster was flattering it;")
print("     if STRONGER, survivorship works in the overlay's favour as previously recorded.")
