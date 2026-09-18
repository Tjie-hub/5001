import sys,os; sys.path.insert(0,"."); sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from base import *
from data.db import connect
df=panel(); S=snapshots(df)

print("=== 12. SECTOR concentration of the excluded names ===")
sec=None
with connect(read_only=True) as c:
    tabs=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for t in ['idx_tickers','tickers','ticker_sector','sectors']:
        if t in tabs:
            cols=[r[1] for r in c.execute(f"PRAGMA table_info({t})")]
            if any('sector' in x.lower() for x in cols):
                sc=[x for x in cols if 'sector' in x.lower()][0]
                tc=[x for x in cols if x.lower() in ('ticker','symbol','code')][0]
                sec=pd.read_sql(f"SELECT {tc} ticker,{sc} sector FROM {t}",c); break
if sec is None or sec.sector.isna().all():
    print("  no usable sector map in DB -> cannot test sector concentration")
else:
    sec=sec.dropna(); m=dict(zip(sec.ticker,sec.sector))
    S['sector']=S.ticker.map(m)
    cov=100*S.sector.notna().mean()
    print(f"  sector coverage of eligible universe: {cov:.1f}%")
    ex=[]
    for pm,g in S.groupby('pm'):
        if len(g)<50: continue
        q=g.park60.quantile(0.90); ex.append(g[g.park60>=q])
    E=pd.concat(ex)
    a=E.sector.value_counts(normalize=True)*100
    b=S.sector.value_counts(normalize=True)*100
    cmp=pd.DataFrame({'excluded %':a,'universe %':b}).dropna()
    cmp['tilt']=cmp['excluded %']-cmp['universe %']
    print(cmp.sort_values('tilt',ascending=False).head(8).to_string(float_format=lambda x:f"{x:.1f}"))

print("\n=== 13. Does the overlay STACK with the 002 trend trades? ===")
SP="/tmp/claude-1000/-home-tjiesar-10-Projects-idx-walkforward-5001/4c28ed38-ba47-47ce-9b0d-30124758261c/scratchpad"
T=pd.read_pickle(f"{SP}/trades002.pkl"); T['date']=pd.to_datetime(T.date)
V=df[['ticker','date','park60','adv60','close']].dropna(subset=['park60'])
M=T.merge(V,on=['ticker','date'],how='left').dropna(subset=['park60'])
print(f"  002 trades with a vol rank at entry: {len(M)} of {len(T)}")
# rank within the eligible cross-section on that date
def pct_rank(g): return g.rank(pct=True)
snap=df[df.adv60.notna()&(df.close>=50)&df.park60.notna()]
rk=snap.groupby('date',group_keys=False).park60.apply(pct_rank)
snap=snap.assign(vrank=rk)[['ticker','date','vrank']]
M=M.merge(snap,on=['ticker','date'],how='left').dropna(subset=['vrank'])
print(f"  with cross-sectional rank: {len(M)}")
for lo,hi,lab in [(0,.5,'bottom half vol'),(.5,.8,'50-80th pct'),(.8,.9,'80-90th'),(.9,1.01,'TOP DECILE vol')]:
    g=M[(M.vrank>=lo)&(M.vrank<hi)]
    if len(g)<30: continue
    mm,t,p,n=stat(g.exc.values)
    print(f"  {lab:18} n={n:5}  excess {mm:+.2f}%/trade  t={t:5.2f}  win={p:.0f}%")
