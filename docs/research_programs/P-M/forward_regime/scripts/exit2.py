import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',270)
R=pd.read_pickle(f"{SP}/trades.pkl"); R=R[R.mkt.notna()]
order=['hold20','hold60','flip','ema','vwma','atr2','atr3','stop8','ema_or_stop']
def tab(S,title):
    o=[]
    for r in order:
        s=S[S.rule==r]
        if len(s)<30: continue
        exc=s.net.values-s.mkt.values
        mu,t=cluster_t(exc,s.date.values)
        # per-day-of-exposure efficiency
        o.append((r,len(s),100*s.net.mean(),100*s.net.median(),mu*100,t,
                  100*(s.net>0).mean(),s.days.mean(),100*s.mae.mean(),
                  mu*100/max(s.days.mean(),1)*20))
    print(f"\n=== {title} ===")
    print(pd.DataFrame(o,columns=['exit rule','N','net%','med%','exc%','t','win%','days','MAE%','exc per 20d']
          ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
tab(R,"ALL uptrend episodes (net of 0.60% round trip, excess vs IHSG)")
q=R[R.rule=='hold20'][['ticker','date','slope']].copy()
cut=q.slope.quantile(0.8)
steep=set(map(tuple,q[q.slope>=cut][['ticker','date']].values))
R['steep']=[ (t,dd) in steep for t,dd in zip(R.ticker,R.date)]
tab(R[R.steep],"STEEP cohort only (slope Q5 — the SMMT-April danger zone)")
tab(R[~R.steep],"NON-steep cohort (slope Q1-Q4)")
