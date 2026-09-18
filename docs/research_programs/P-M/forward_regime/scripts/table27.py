import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings, itertools; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',280)
S=pd.read_pickle(f"{SP}/tiers.pkl")
T=pd.read_pickle(f"{SP}/trades002.pkl"); T['date']=pd.to_datetime(T.date)
T=T.merge(S,on='date',how='inner')
print("spec-002 onset trades with a full 3-tier state: %d of %d"%(len(T),len(pd.read_pickle(f"{SP}/trades002.pkl"))))
rows=[]
for L,M,Sh in itertools.product(['BULL','SIDEWAYS','BEAR'],repeat=3):
    g=T[(T.LONG==L)&(T.MID==M)&(T.SHORT==Sh)]
    sess=len(S[(S.LONG==L)&(S.MID==M)&(S.SHORT==Sh)])
    if len(g)==0:
        rows.append((L,M,Sh,sess,0,0,np.nan,np.nan,np.nan,np.nan)); continue
    mu,t=(cluster_t(g.exc.values,g.date.values) if len(g)>=20 else (np.nan,np.nan))
    rows.append((L,M,Sh,sess,len(g),g.date.dt.to_period('M').nunique(),
                 100*g.net.mean(),mu*100,t,100*(g.net>0).mean()))
R=pd.DataFrame(rows,columns=['LONG','MID','SHORT','sessions','trades','months','net%','excess%','t','win%'])
R['align']=np.where((R.LONG==R.MID)&(R.MID==R.SHORT),'ALL MATCH','mixed')
print()
print("=== 27-STATE POSSIBILITY TABLE (spec-002 onset, 3xATR exit, net 0.60%) ===")
print(R.sort_values('net%',ascending=False).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
R.to_pickle(f"{SP}/table27.pkl")

print("\n\n=== WHY: do the tiers ever align BULL? ===")
for c in ['LONG','MID','SHORT']:
    print(f"  {c:6s} BULL on {int((S[c]=='BULL').sum()):4d} of {len(S)} sessions")
print("  LONG&MID both BULL :",int(((S.LONG=='BULL')&(S.MID=='BULL')).sum()))
print("  MID&SHORT both BULL:",int(((S.MID=='BULL')&(S.SHORT=='BULL')).sum()))
print("  ALL THREE BULL     :",int(((S.LONG=='BULL')&(S.MID=='BULL')&(S.SHORT=='BULL')).sum()))
print("  ALL THREE BEAR     :",int(((S.LONG=='BEAR')&(S.MID=='BEAR')&(S.SHORT=='BEAR')).sum()))

print("\n=== ROBUST AGGREGATION: alignment SCORE (BULL=+1, SIDEWAYS=0, BEAR=-1, summed) ===")
sc={'BULL':1,'SIDEWAYS':0,'BEAR':-1}
for df_ in (S,T):
    df_['score']=df_.LONG.map(sc)+df_.MID.map(sc)+df_.SHORT.map(sc)
rows=[]
for v in range(-3,4):
    g=T[T.score==v]; sess=int((S.score==v).sum())
    if len(g)<20: rows.append((v,sess,len(g),np.nan,np.nan,np.nan,np.nan)); continue
    mu,t=cluster_t(g.exc.values,g.date.values)
    rows.append((v,sess,len(g),g.date.dt.to_period('M').nunique(),100*g.net.mean(),mu*100,t))
A=pd.DataFrame(rows,columns=['score','sessions','trades','months','net%','excess%','t'])
print(A.to_string(index=False,float_format=lambda x:f"{x:.2f}"))
cur=S.iloc[-1]
print("\ncurrent state: LONG=%s MID=%s SHORT=%s -> score %+d"%(cur.LONG,cur.MID,cur.SHORT,cur.score))
g=T[T.score==cur.score]
mu,t=cluster_t(g.exc.values,g.date.values)
print("  historical at this score: %d trades, net %+.2f%%, excess %+.2f%% (t %.2f), win %.0f%%"%(
    len(g),100*g.net.mean(),mu*100,t,100*(g.net>0).mean()))

print("\n=== ERA CHECK: does the score ordering survive outside 2025? ===")
T['yr']=T.date.dt.year
rows=[]
for v in range(-3,3):
    g=T[T.score==v]; ex=g[g.yr!=2025]
    r=[v,len(g),100*g.net.mean(),len(ex),100*ex.net.mean() if len(ex)>=20 else np.nan]
    if len(ex)>=20:
        mu,t=cluster_t(ex.exc.values,ex.date.values); r+= [mu*100,t]
    else: r+=[np.nan,np.nan]
    yrs=g.groupby('yr').net.mean()*100
    r.append("/".join(f"{y%100:02d}:{v_:+.0f}" for y,v_ in yrs.items() if g[g.yr==y].shape[0]>=15))
    rows.append(r)
print(pd.DataFrame(rows,columns=['score','N_all','net_all%','N_ex25','net_ex25%','exc_ex25%','t','by year']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
