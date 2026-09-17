import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',260); COST=0.006
d=pd.read_pickle(f"{SP}/panel2.pkl").sort_values(['ticker','date']).reset_index(drop=True)
g=d.groupby('ticker',sort=False)
d['ema10']=g['close'].transform(lambda s:s.ewm(span=10,adjust=False,min_periods=10).mean())
d['ema20_']=g['close'].transform(lambda s:s.ewm(span=20,adjust=False,min_periods=20).mean())
d['v20']=g['volume'].transform(lambda s:s.rolling(20,min_periods=15).mean()).groupby(d.ticker).shift(1)
d['nz']=(d.volume>0).astype(int)
d['nz20']=g['nz'].transform(lambda s:s.shift(1).rolling(20,min_periods=20).sum())
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)&(d.volume>0)&(d.nz20>=18)).fillna(False).astype(bool)
def slope(s,w=20):
    x=np.arange(w); xm=x.mean(); den=((x-xm)**2).sum()
    return s.rolling(w,min_periods=w).apply(lambda y:((x-xm)*(y-y.mean())).sum()/den,raw=True)
d['sh']=g['high'].transform(lambda s:slope(s))
d['slo']=g['low'].transform(lambda s:slope(s))
# range of first vs last 5 bars of the 20-bar window (true tightening)
d['r_early']=(g['high'].transform(lambda s:s.shift(15).rolling(5,min_periods=5).max())
             -g['low'].transform(lambda s:s.shift(15).rolling(5,min_periods=5).min()))
d['r_late'] =(g['high'].transform(lambda s:s.rolling(5,min_periods=5).max())
             -g['low'].transform(lambda s:s.rolling(5,min_periods=5).min()))
for cc in ['sh','slo','r_early','r_late','ema10','ema20_']: d[cc+'_1']=g[cc].shift(1)
d['e20s_1']=(d.ema20_/g['ema20_'].shift(10)-1).groupby(d.ticker).shift(1)
d['c1']=g['close'].shift(1)
base=d.liq&(d.c1<d.ema20__1)&(d.e20s_1<0)&(d.sh_1<0)&(d.slo_1<0)&(d.close>d.ema10)&(d.c1<=d.ema10_1)&(d.volume>1.2*d.v20)
conv_ratio=d.sh_1/d.slo_1                      # >1 means highs falling faster (converging)
tighten=d.r_late_1/d.r_early_1                 # <1 means range contracting
defs={
 'W1 loose (my original: sh<slo)'      : base&(d.sh_1<d.slo_1),
 'W2 highs fall >=25% faster'          : base&(conv_ratio>=1.25),
 'W3 highs fall >=50% faster'          : base&(conv_ratio>=1.50),
 'W4 range tightens >=30%'             : base&(tighten<=0.70),
 'W5 range tightens >=50%'             : base&(tighten<=0.50),
 'W6 strict: >=50% faster AND >=30% tighter': base&(conv_ratio>=1.50)&(tighten<=0.70),
}
rows=[]
for nm,m in defs.items():
    m=m.fillna(False)
    s=d[m&d.f20.notna()&d.m20.notna()&(d.bad20.fillna(1)==0)]
    if len(s)<40: rows.append((nm,int(m.sum()),np.nan,np.nan,np.nan)); continue
    mu,t=cluster_t((s.f20-COST-s.m20).values,s.date.values)
    s5=d[m&d.f5.notna()&d.m5.notna()&(d.bad5.fillna(1)==0)]
    mu5,t5=cluster_t((s5.f5-COST-s5.m5).values,s5.date.values)
    rows.append((nm,len(s),mu5*100,t5,mu*100,t))
print("=== does a STRICTER wedge definition rescue it? (panel, all history) ===")
print(pd.DataFrame(rows,columns=['wedge definition','N','exc5%','t','exc20%','t']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
