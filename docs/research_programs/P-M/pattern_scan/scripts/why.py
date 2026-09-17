import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',260); COST=0.006
d=pd.read_pickle(f"{SP}/panel2.pkl").sort_values(['ticker','date']).reset_index(drop=True)
g=d.groupby('ticker',sort=False)
d['nz']=(d.volume>0).astype(int)
d['nz20']=g['nz'].transform(lambda s:s.shift(1).rolling(20,min_periods=20).sum())
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)&(d.volume>0)&(d.nz20>=18)).fillna(False).astype(bool)
d['lo20']=g['low'].transform(lambda s:s.rolling(20,min_periods=20).min()).groupby(d.ticker).shift(1)
d['exc20']=d.f20-COST-d.m20
ok=d.liq&d.exc20.notna()&(d.bad20.fillna(1)==0)
sig=ok&(d.low<d.lo20)&(d.close>d.lo20)          # failed breakdown
D=d[ok].copy()
# each ticker's OWN unconditional mean excess (its drift)
D['tk_mean']=D.groupby('ticker')['exc20'].transform('mean')
D['demeaned']=D.exc20-D.tk_mean
S=D[sig.reindex(D.index,fill_value=False)]
mu,t=cluster_t(S.exc20.values,S.date.values)
mud,td=cluster_t(S.demeaned.values,S.date.values)
print("FAILED BREAKDOWN, panel (N=%d, %d tickers)"%(len(S),S.ticker.nunique()))
print("  raw excess vs IHSG          : %+.2f%%  t=%.2f"%(100*mu,t))
print("  MINUS each ticker's own drift: %+.2f%%  t=%.2f   <- pure within-ticker effect"%(100*mud,td))
print("  (universe mean ticker drift  : %+.2f%%)"%(100*D.tk_mean.mean()))
print()
# per-ticker effect distribution; where does BRPT sit?
per=S.groupby('ticker').exc20.agg(['mean','size'])
per=per[per['size']>=10]
b=per.loc['BRPT','mean']*100 if 'BRPT' in per.index else np.nan
print("per-ticker mean effect (tickers with >=10 signals, n=%d)"%len(per))
print("  share of tickers POSITIVE : %.0f%%"%(100*(per['mean']>0).mean()))
print("  median ticker             : %+.2f%%"%(100*per['mean'].median()))
print("  BRPT                      : %+.2f%%  -> percentile %.0f"%(b,100*(per['mean']<per.loc['BRPT','mean']).mean()))
print("  10th/90th pct             : %+.2f%% / %+.2f%%"%(100*per['mean'].quantile(.1),100*per['mean'].quantile(.9)))
