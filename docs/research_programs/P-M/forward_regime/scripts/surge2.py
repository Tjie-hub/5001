import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.environ['SP']; pd.set_option('display.width',250)
df=pd.read_pickle(f"{SP}/panel2.pkl").reset_index(drop=True)
g=df.groupby('ticker',sort=False)
df['surge']=((df.ret>=0.10)&(df.vol_ratio>=5.0)&(df.bad==0)).astype(int)
# quiet window t+1..t+5 (no surge), then FUTURE surge in t+6..t+15
df['q5'] =g['surge'].transform(lambda s:s.shift(-5).rolling(5,min_periods=5).max())   # t+1..t+5
df['fut']=g['surge'].transform(lambda s:s.shift(-15).rolling(10,min_periods=10).max())# t+6..t+15
df['prior5']=g['surge'].transform(lambda s:s.shift(1).rolling(5,min_periods=1).max()) # t-5..t-1
liq=(df.adv20>=1e9)&(df.close>=50)&(df.n>=25)
L=df[liq&df.fut.notna()&df.q5.notna()].copy()
# CLEAN BASELINE: days with no surge at t and none in prior 5d, and quiet t+1..t+5
clean = (L.surge==0)&(L.prior5==0)&(L.q5==0)
B=L[clean]; base=B.fut.mean()
print("clean anchor days: %d | BASELINE P(surge in t+6..t+15) = %.2f%%"%(len(B),100*base))
print()
shock=(L.vol_ratio>=4.0)&(L.close_pos>=0.80)&(L.ret>=0.03)&(L.surge==0)   # shock but NOT itself a surge
rows=[]
for nm,m in [("shock@t, NOT a surge, then 5 quiet days",shock&(L.q5==0)&(L.prior5==0)),
             ("shock@t (surge allowed prior), 5 quiet",shock&(L.q5==0)),
             ("dry base only, 5 quiet days",(L.dry<=1.0)&(L.surge==0)&(L.q5==0)&(L.prior5==0)),
             ("ANY surge in prior 5d, then 5 quiet",(L.prior5==1)&(L.q5==0))]:
    s=L[m.fillna(False)]
    if len(s)<30: continue
    p=s.fut.mean()
    # date-clustered SE on the proportion
    from panel import cluster_t
    mu,t=cluster_t(s.fut.values-base, s.date.values)
    rows.append((nm,len(s),100*p,p/base,t))
print(pd.DataFrame(rows,columns=['precursor (surge-separated)','N','P(surge t+6..t+15)%','LIFT x','t vs base']).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
