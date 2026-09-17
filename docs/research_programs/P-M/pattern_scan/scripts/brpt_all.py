import os,sys; sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'.')
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
from engine.smc import detect_liquidity_sweep
SP=os.environ['SP']; pd.set_option('display.width',260); COST=0.006
d=pd.read_pickle(f"{SP}/panel2.pkl").sort_values(['ticker','date']).reset_index(drop=True)
d=d[d.ticker=='BRPT'].reset_index(drop=True)
c=d.close; h=d.high; l=d.low
d['ema10']=c.ewm(span=10,adjust=False,min_periods=10).mean()
d['ema20_']=c.ewm(span=20,adjust=False,min_periods=20).mean()
d['v20']=d.volume.rolling(20,min_periods=15).mean().shift(1)
d['hi20']=h.rolling(20,min_periods=20).max().shift(1)
d['lo20']=l.rolling(20,min_periods=20).min().shift(1)
d['pc']=c.shift(1)
def slope(s,w=20):
    x=np.arange(w); xm=x.mean(); den=((x-xm)**2).sum()
    return s.rolling(w,min_periods=w).apply(lambda y:((x-xm)*(y-y.mean())).sum()/den,raw=True)
d['sh']=(slope(h)/c).shift(1); d['slo']=(slope(l)/c).shift(1)
d['rng20']=((h.rolling(20,min_periods=20).max()-l.rolling(20,min_periods=20).min())/c).shift(1)
d['rng40']=((h.rolling(40,min_periods=40).max()-l.rolling(40,min_periods=40).min())/c).shift(1)
d['e20s']=(d.ema20_/d.ema20_.shift(10)-1).shift(1)
# production liquidity sweep
sw=detect_liquidity_sweep(d[['date','open','high','low','close','volume']].copy())
bull=set(sw[sw.signal==1].date.astype(str).str[:10]) if not sw.empty else set()
d['dstr']=d.date.astype(str).str[:10]
P={}
P['LIQ SWEEP (PDL/PWL bull)'] = d.dstr.isin(bull)
P['FAILED BREAKDOWN (20d low)'] = (l<d.lo20)&(c>d.lo20)
P['RESISTANCE BREAKOUT'] = c>d.hi20
P['FAILED BREAKOUT (bull trap)'] = (h>d.hi20)&(c<d.hi20)
P['WEDGE POP (Kell)'] = ((c.shift(1)<d.ema20_.shift(1))&(d.e20s<0)&(d.sh<0)&(d.slo<0)&(d.sh<d.slo)
                          &(d.rng20<0.8*d.rng40)&(c>d.ema10)&(c.shift(1)<=d.ema10.shift(1))&(d.volume>1.2*d.v20))
P['EPISODIC PIVOT (gap>=5%,3x vol)'] = ((d.open/d.pc-1>=0.05)&(d.open/d.pc-1<=0.25)&(d.volume>=3*d.v20))
rows=[]
for nm,m in P.items():
    m=m.fillna(False)
    s=d[m&d.f20.notna()]
    if len(s)==0: rows.append((nm,0,np.nan,np.nan,np.nan)); continue
    e20=(s.f20-COST-s.m20)*100
    e5=(s.f5-COST-s.m5)*100
    rows.append((nm,int(m.sum()),e5.mean(),e20.mean(),100*(e20>0).mean()))
print("=== BRPT: every pattern from today, on this one ticker ===")
print(pd.DataFrame(rows,columns=['pattern','signals','mean exc5%','mean exc20%','win20%']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
print()
print("panel-wide ex-2025 for comparison: sweep -1.33 | failed bd -1.94 | wedge -1.89 | resist bo +0.40")
# dates for charting (2025-2026 window)
w=d[d.date>='2025-01-01']
for nm,m in P.items():
    dts=w[m.fillna(False).reindex(w.index,fill_value=False)].dstr.tolist()
    print(f"\n{nm}: {len(dts)} in 2025-26")
    print("  ",", ".join(dts[:14]) + (" ..." if len(dts)>14 else ""))

print("\n\n=== the mechanism: BRPT's own drift vs the patterns ===")
d['yr']=pd.DatetimeIndex(d.date).year
base=d[d.f20.notna()]
print("BRPT UNCONDITIONAL mean 20d excess (every bar, no pattern): %+.2f%%"%(((base.f20-base.m20)*100).mean()))
print("BRPT price 2025-01-02 -> 2026-09-16: %.0f -> %.0f (%+.0f%%)"%(
    d[d.date>='2025-01-01'].close.iloc[0], d.close.iloc[-1],
    100*(d.close.iloc[-1]/d[d.date>='2025-01-01'].close.iloc[0]-1)))
print()
print("=== same patterns, split 2025 vs 2026 ===")
rows=[]
for nm,m in P.items():
    m=m.fillna(False)
    r=[nm]
    for y in [2025,2026]:
        s=d[m&(d.yr==y)&d.f20.notna()]
        r+= [len(s), ((s.f20-COST-s.m20)*100).mean() if len(s)>=3 else np.nan]
    rows.append(r)
print(pd.DataFrame(rows,columns=['pattern','N 2025','exc20 2025%','N 2026','exc20 2026%']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))

print("\n\n=== ABSOLUTE vs EXCESS: BRPT 2026 (IHSG fell -23.8%) ===")
rows=[]
for nm,m in P.items():
    m=m.fillna(False)
    s=d[m&(d.yr==2026)&d.f20.notna()]
    if len(s)<3: continue
    raw=((s.f20-COST)*100); exc=((s.f20-COST-s.m20)*100)
    rows.append((nm,len(s),raw.mean(),exc.mean(),100*(raw>0).mean()))
print(pd.DataFrame(rows,columns=['pattern (2026)','N','ABS net20%','excess20%','win_abs%']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
print()
print(">>> excess can be strongly POSITIVE while absolute return is NEGATIVE,")
print("    because the benchmark fell harder. You cannot eat relative performance.")
