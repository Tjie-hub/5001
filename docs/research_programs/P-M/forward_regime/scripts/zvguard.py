import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',240)
d=pd.read_pickle(f"{SP}/ma.pkl")
d=d[d.ticker!='IHSG'].sort_values(['ticker','date']).reset_index(drop=True)
g=d.groupby('ticker',sort=False)
d['sl']=g['slope'].shift(1); d['er']=g['ER'].shift(1); d['pa']=g['pct_above'].shift(1)
d['UP']=((d.sl>0.02)&(d.er>=0.30)&(d.pa>=0.70)).fillna(False).astype(bool)
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)).fillna(False).astype(bool)
d['nz']=(d.volume>0).astype(int)
g2=d.groupby('ticker',sort=False)
d['nz20']=g2['nz'].transform(lambda s:s.shift(1).rolling(20,min_periods=20).sum())
prev=g2['UP'].shift(1).fillna(False).astype(bool)
d['onset']=d.UP&d.liq&(~prev)
YR=pd.DatetimeIndex(d.date).year
ok=d.f20.notna()&d.m20.notna()&(d.bad20.fillna(1)==0)
EX=(d.f20-d.m20).values; DT=d.date.values
rows=[]
for nm,m in [('V0 no guard (= spec 001)', d.onset),
             ('V1 entry volume > 0',      d.onset&(d.nz==1)),
             ('V2 V1 + >=18/20 traded',   d.onset&(d.nz==1)&(d.nz20>=18)),
             ('V3 V1 + 20/20 traded',     d.onset&(d.nz==1)&(d.nz20>=20))]:
    sub=(m&ok).values
    mu,t=cluster_t(EX[sub],DT[sub])
    s2=(m&ok&(YR!=2025)).values
    mu2,t2=cluster_t(EX[s2],DT[s2])
    rows.append((nm,int(sub.sum()),100*sub.sum()/int((d.onset&ok).sum()),mu*100,t,mu2*100,t2))
print(pd.DataFrame(rows,columns=['variant','entries','% kept','excess20 FULL%','t','excess20 ex25%','t']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
print()
print("LIFE check under V2 -- would any 2026 LIFE bar pass the traded-days guard?")
lf=d[(d.ticker=='LIFE')&(d.date>='2026-09-01')]
print(lf[['date','close','volume','nz20','liq','UP']].to_string(index=False))
