import os,sys; sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'.')
import pandas as pd, numpy as np, warnings, collections; warnings.filterwarnings('ignore')
exec(open(os.environ['SP']+'/port.py').read().split("def curve")[0])
def curve(rt):
    buy,sell=rt*0.4,rt*0.6          # IDX: sell leg heavier (0.1% sales tax)
    rr=[]
    for dd in cal:
        names=hold.get(dd,[]); n=len(names)
        if n==0: rr.append(0.0); continue
        r=np.nanmean(ret.loc[dd,names].values); w=1.0/n
        c=w*buy*len([t for t in entd.get(dd,[]) if t in names])+w*sell*len([t for t in extd.get(dd,[]) if t in names])
        rr.append((0.0 if np.isnan(r) else r)-c)
    return pd.Series(rr,index=cal)
ihr=ihs.reindex(cal).pct_change().fillna(0); msk=pd.DatetimeIndex(cal).year!=2025
def cg(s): eq=(1+s).cumprod(); return 100*(eq.iloc[-1]**(252/len(s))-1)
rows=[]
for rt in [0.000,0.004,0.005,0.006,0.007,0.008,0.010,0.012]:
    S=curve(rt); e=S-ihr
    rows.append((100*rt,cg(e),cg(e[msk]),e[msk].mean()/e[msk].std()*np.sqrt(252),cg(S),cg(S[msk])))
R=pd.DataFrame(rows,columns=['round trip %','exc CAGR full%','exc CAGR ex25%','Sharpe ex25','abs CAGR full%','abs CAGR ex25%'])
print(R.to_string(index=False,float_format=lambda x:f"{x:.2f}"))
g=R.iloc[0]['exc CAGR ex25%']; d=(g-R[R['round trip %']==0.6]['exc CAGR ex25%'].iloc[0])/0.6
print("\ngross ex-2025 excess = %.2f%%/yr | drag = %.2f%%/yr per 0.1%% of round trip"%(g,d/10))
print("breakeven round trip (ex-2025) = %.2f%%"%(g/d))
