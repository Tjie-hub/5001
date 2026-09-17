import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',250)
R=pd.read_pickle(f"{SP}/ihsg_regime.pkl")
T=pd.read_pickle(f"{SP}/trades002.pkl")   # atr3 trades, 002 universe
T['date']=pd.to_datetime(T.date)
T=T.merge(R.rename(columns={'date':'date'}),on='date',how='left')
print("=== trend strategy (FWD-PM-REGIME-002 spec) by IHSG regime AT ENTRY ===")
rows=[]
for rg,g in T.groupby('regime'):
    mu,t=cluster_t(g.exc.values,g.date.values)
    rows.append((rg,len(g),g.date.dt.to_period('M').nunique(),100*g.net.mean(),mu*100,t,100*(g.net>0).mean()))
print(pd.DataFrame(rows,columns=['IHSG regime','trades','distinct months','net/trade%','excess%','t','win%']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
print()
# how many INDEPENDENT episodes back each regime?
ep=R.copy(); ep['blk']=(ep.regime!=ep.regime.shift()).cumsum()
cnt=ep.groupby(['regime']).blk.nunique()
sess=ep.regime.value_counts()
print("=== feasibility of regime-conditional fitting ===")
for rg in ['BULL','BEAR','SIDEWAYS']:
    print("  %-9s %3d independent episodes, %4d sessions"%(rg,cnt.get(rg,0),sess.get(rg,0)))
print()
print("  pre-registered regime_config.yaml requires min_n = 100 PER CELL")
print("  primary x vol-tier x liq-tier = 3 x 2 x 2 = 12 cells")
print("  BULL has %d sessions TOTAL -> cannot fill even one 100-obs cell after splitting"%sess.get('BULL',0))
