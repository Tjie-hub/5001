import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',250)
d=pd.read_pickle(f"{SP}/ma.pkl"); g=d.groupby('ticker',sort=False)
d['sl']=g['slope'].shift(1); d['er']=g['ER'].shift(1); d['pa']=g['pct_above'].shift(1)
d=d[d.ticker!='IHSG']
ok=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)&d.f20.notna()&d.m20.notna()&(d.bad20.fillna(1)==0)).values
SL,ER,PA=d.sl.values,d.er.values,d.pa.values
EX=(d.f20.values-d.m20.values); DT=d.date.values; YR=pd.DatetimeIndex(d.date).year.values
print("=== per-YEAR excess: chosen vs tightened ===")
specs={'CHOSEN  .02/.30/.70':(0.02,0.30,0.70),'TIGHT   .10/.40/.90':(0.10,0.40,0.90),'TIGHTEST .10/.50/.90':(0.10,0.50,0.90)}
rows=[]
for nm,(s,e,p) in specs.items():
    m=ok&(SL>s)&(ER>=e)&(PA>=p)
    r={'spec':nm,'N':int(m.sum())}
    for y in range(2021,2027):
        sub=m&(YR==y)
        r[y]=cluster_t(EX[sub],DT[sub])[0]*100 if sub.sum()>50 else np.nan
    sub=m&(YR!=2025); mu,t=cluster_t(EX[sub],DT[sub]); r['ex25']=mu*100; r['ex25_t']=t
    rows.append(r)
print(pd.DataFrame(rows).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
print("\n>>> 'ex25' is the honest comparison: does tightening help OUTSIDE the blowout year?")
