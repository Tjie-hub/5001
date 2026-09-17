import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, itertools, warnings, pickle
warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',260)
b=pd.read_pickle(f"{SP}/base.pkl"); pre=pickle.load(open(f"{SP}/pre.pkl","rb"))
vr=b.vol_ratio.values; cp=b.close_pos.values; rt=b.ret.values; dry=b.dry.values
cl=b.close.values; vol=b.volume.values
liq0=(b.adv20.values>=1e9)&(cl>=50)&(b.n.values>=25)
rows=[]
for VS,CP,DRY,W,RUN,VDRY in itertools.product([2.5,3.0,4.0,6.0],[0.70,0.80],[1.0,99.0],[3,5,8],[1.15,1.30,99.0],[0.50,0.80,99.0]):
    d=pre[W]
    shock=(vr>=VS)&(cp>=CP)&(rt>=0.03)&(dry<=DRY)
    ab=(d['maxh']<=cl*RUN)&(d['minl']>=cl*0.92)&(d['meanv']<=vol*VDRY)
    m=shock&ab&liq0&(d['bad_ab']==0)&~np.isnan(d['e_adv20'])
    if m.sum()<30: continue
    for h in [5,10,20]:
        ok=m&(np.nan_to_num(d[f'e_bad{h}'],nan=1)==0)&~np.isnan(d[f'e_f{h}'])
        n=int(ok.sum())
        if n<30: continue
        f=d[f'e_f{h}'][ok]; mk=d[f'e_m{h}'][ok]; dt=d['e_date'][ok]
        mu,t=cluster_t(f-mk,dt)
        rows.append(dict(VS=VS,CP=CP,DRY=DRY,W=W,RUN=RUN,VDRY=VDRY,h=h,N=n,
                    tk=b.ticker.values[ok].nunique() if hasattr(b.ticker.values[ok],'nunique') else len(set(b.ticker.values[ok])),
                    net=(f.mean()-0.006)*100,exc=mu*100,t=t,win=(f>0.006).mean()*100))
r=pd.DataFrame(rows); r.to_pickle(f"{SP}/grid.pkl")
print("cells evaluated:",len(r))
print("mean excess over ALL cells: %+.3f%% | median t: %+.2f"%(r.exc.mean(),r.t.median()))
print("t>+1.96: %d (%.1f%%)   t<-1.96: %d (%.1f%%)"%((r.t>1.96).sum(),(r.t>1.96).mean()*100,(r.t<-1.96).sum(),(r.t<-1.96).mean()*100))
print("\n--- TOP 10 by t ---");  print(r.nlargest(10,'t').to_string(index=False,float_format=lambda x:f"{x:.2f}"))
print("\n--- BOTTOM 5 by t ---"); print(r.nsmallest(5,'t').to_string(index=False,float_format=lambda x:f"{x:.2f}"))
print("\n--- t by horizon ---"); print(r.groupby('h')['t'].agg(['count','mean','median','max']).to_string())
print("\n--- t by absorption strictness (RUN cap) ---"); print(r.groupby('RUN')[['exc','t']].mean().to_string())
print("--- t by volume-dry (VDRY) ---"); print(r.groupby('VDRY')[['exc','t']].mean().to_string())
