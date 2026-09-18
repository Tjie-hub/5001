import sys,os; sys.path.insert(0,"."); sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from base import *
df=panel()
SP="/tmp/claude-1000/-home-tjiesar-10-Projects-idx-walkforward-5001/4c28ed38-ba47-47ce-9b0d-30124758261c/scratchpad"
T=pd.read_pickle(f"{SP}/trades002.pkl"); T['date']=pd.to_datetime(T.date)
snap=df[df.adv60.notna()&(df.close>=50)&df.park60.notna()].copy()
snap['vrank']=snap.groupby('date',group_keys=False).park60.rank(pct=True)
M=T.merge(snap[['ticker','date','vrank']],on=['ticker','date'],how='left').dropna(subset=['vrank'])
M['exc']*=100
print(f"002 trades with a cross-sectional vol rank: {len(M)} of {len(T)}\n")
def blk(lab,d):
    print(f"  --- {lab} (n={len(d)}) ---")
    for lo,hi,l2 in [(0,.5,'bottom half vol'),(.5,.8,'50-80th pct'),
                     (.8,.9,'80-90th pct'),(.9,1.01,'TOP DECILE (excluded by VOLEX)')]:
        g=d[(d.vrank>=lo)&(d.vrank<hi)]
        if len(g)<30: continue
        mm,t,p,n=stat(g.exc.values)
        print(f"    {l2:32} n={n:5}  excess {mm:+6.2f}%/trade  t={t:5.2f}  win={p:.0f}%")
blk("ALL ERA",M); blk("EX-2025",M[M.yr!=2025])
print("\n  => if the top decile is NOT negative here, VOLEX exclusion does not stack with 002")

print("\n=== 14. MULTIPLICITY accounting for this session's VOLEX sweep ===")
specs=[("universe constructions",4),("exclusion fractions",7),("estimators",6),
       ("rebalance staleness",5),("confound overlays",4),("book sizes (bootstrap)",6),
       ("era splits",3),("002 vol strata",4)]
tot=sum(n for _,n in specs)
for l,n in specs: print(f"    {l:28} {n}")
print(f"    {'TOTAL specs evaluated':28} {tot}")
best_t=3.49
from math import erfc,sqrt
p_one=0.5*erfc(best_t/sqrt(2))
print(f"\n  best single t observed  : {best_t:.2f}  (one-sided p = {p_one:.5f})")
print(f"  Sidak-adjusted p over {tot}: {1-(1-p_one)**tot:.4f}")
print(f"  Bonferroni threshold t for {tot} specs at 5%: "
      f"{abs(__import__('scipy.stats',fromlist=['norm']).norm.ppf(0.05/tot)):.2f}")
