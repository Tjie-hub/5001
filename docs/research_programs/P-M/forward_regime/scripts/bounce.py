import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',260)
d=pd.read_pickle(f"{SP}/ma.pkl")
g=d.groupby('ticker',sort=False)
liq=(d.adv20>=1e9)&(d.close>=50)&(d.n>=25)
for MA in ['ema20','vwma20']:
    d[f'pc_ab_{MA}']=(g['close'].shift(1)>g[MA].shift(1))
    d[f'touch_{MA}']=d[f'pc_ab_{MA}']&(d.low<=d[MA])&(d.close>0)
    d[f'back_{MA}']=(g['close'].shift(-3)>g[MA].shift(-3))      # reclaimed MA 3d later
# regime from state at t-1 (no look-ahead)
sl=g['slope'].shift(1); er=g['ER'].shift(1); pa=g['pct_above'].shift(1); cr=g['cross'].shift(1)
UP  =(sl>0.02)&(er>=0.30)&(pa>=0.70)
SIDE=(sl.abs()<0.01)&(er<0.20)&(cr>=4)
print("regime coverage (liquid days): UP %.1f%%  SIDE %.1f%%"%(100*UP[liq].mean(),100*SIDE[liq].mean()))
rows=[]
for MA in ['ema20','vwma20']:
  for rn,R in [('UPTREND',UP),('SIDEWAYS',SIDE)]:
    T=d[liq&R&d[f'touch_{MA}']&d.f5.notna()&d.m5.notna()&(d.bad5.fillna(1)==0)]
    A=d[liq&R&d.f5.notna()&d.m5.notna()&(d.bad5.fillna(1)==0)]        # ALL days in regime = control
    if len(T)<50: continue
    mu_t,t_t=cluster_t(T.f5.values-T.m5.values,T.date.values)
    mu_a,t_a=cluster_t(A.f5.values-A.m5.values,A.date.values)
    rows.append((MA,rn,len(T),100*T[f'back_{MA}'].mean(),100*T.f5.mean(),mu_t*100,
                 len(A),mu_a*100,(mu_t-mu_a)*100))
print("\n=== TOUCH the MA, then hold 5 days ===")
print(pd.DataFrame(rows,columns=['MA','regime','N_touch','reclaim_3d%','raw5%','exc5%','N_all_regime','exc5_ALL%','TOUCH-minus-ALL%']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
print("\n>>> 'TOUCH-minus-ALL' is the only honest number: does touching the MA add anything")
print("    beyond simply being in that regime?\n")
# discriminator separation
print("=== do the discriminators actually separate the two regimes? (liquid days) ===")
st=pd.DataFrame({'ER':d.ER,'slope10':d.slope,'pct_above':d.pct_above,'crossings':d.cross,'vwma-ema%':d.vw_ema*100})
print(pd.concat([st[liq&UP].mean().rename('UPTREND'),st[liq&SIDE].mean().rename('SIDEWAYS')],axis=1).to_string(float_format=lambda x:f"{x:.3f}"))
