import os,sys; sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'.')
import pandas as pd, numpy as np, warnings, time; warnings.filterwarnings('ignore')
from panel import cluster_t
from engine.smc import detect_liquidity_sweep
SP=os.environ['SP']; pd.set_option('display.width',260); COST=0.006
d=pd.read_pickle(f"{SP}/panel2.pkl").sort_values(['ticker','date']).reset_index(drop=True)
g=d.groupby('ticker',sort=False)
d['nz']=(d.volume>0).astype(int)
d['nz20']=g['nz'].transform(lambda s:s.shift(1).rolling(20,min_periods=20).sum())
d['liq']=((d.adv20>=1e9)&(d.close>=50)&(d.n>=25)&(d.volume>0)&(d.nz20>=18)).fillna(False).astype(bool)
tick=[t for t,x in d.groupby('ticker') if x.liq.sum()>50]
print("tickers scanned:",len(tick)); t0=time.time()
hits=[]
for i,tk in enumerate(tick):
    x=d[d.ticker==tk].copy()
    x['date']=pd.to_datetime(x.date)
    sw=detect_liquidity_sweep(x[['date','open','high','low','close','volume']].reset_index(drop=True))
    if sw.empty: continue
    b=sw[sw['signal']==1]
    for ds,st in zip(b['date'],b['sweep_type']):
        hits.append((tk,str(ds)[:10],st))
    if i%200==0: print(f"  {i}/{len(tick)} {time.time()-t0:.0f}s",flush=True)
H=pd.DataFrame(hits,columns=['ticker','dstr','sweep_type'])
print("bullish sweeps found:",len(H),"in",f"{time.time()-t0:.0f}s")
d['dstr']=d.date.astype(str).str[:10]
M=d.merge(H,on=['ticker','dstr'],how='inner')
M=M[M.liq]
print("after liquidity filter:",len(M))
def rep(nm,s):
    out=[nm,len(s),s.ticker.nunique()]
    for h in [5,10,20]:
        ss=s[s[f'f{h}'].notna()&s[f'm{h}'].notna()&(s[f'bad{h}'].fillna(1)==0)]
        if len(ss)<100: out+=[np.nan,np.nan]; continue
        mu,t=cluster_t((ss[f'f{h}']-COST-ss[f'm{h}']).values,ss.date.values); out+=[mu*100,t]
    ss=s[s.f20.notna()&s.m20.notna()&(s.bad20.fillna(1)==0)]
    ss=ss[pd.DatetimeIndex(ss.date).year!=2025]
    mu,t=cluster_t((ss.f20-COST-ss.m20).values,ss.date.values); out+=[mu*100,t]
    return out
rows=[rep('P1 liquidity sweep (production detect_liquidity_sweep)',M)]
for st in sorted(M.sweep_type.unique()):
    s=M[M.sweep_type==st]
    if len(s)>300: rows.append(rep(f'   by type: {st}',s))
print(pd.DataFrame(rows,columns=['pattern','N','tickers','exc5%','t','exc10%','t','exc20%','t','exc20 ex25%','t']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
M.to_pickle(f"{SP}/sweeps.pkl")
