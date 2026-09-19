"""IDX80 reconstitution event study. Additions and deletions derived from
consecutive membership periods; abnormal return = stock return minus the
equal-weight liquid universe over the same window."""
import sys,os; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
with connect(read_only=True) as c:
    M=pd.read_sql("SELECT ticker,period_label,effective_from FROM idx80_membership_history WHERE membership_status='MEMBER'",c)
    o=pd.read_sql("SELECT ticker,date,close,volume FROM ohlcv WHERE is_final=1 AND volume>0",c)
o['date']=pd.to_datetime(o.date); M['effective_from']=pd.to_datetime(M.effective_from)
periods=sorted(M.period_label.unique())
memb={p:set(M[M.period_label==p].ticker) for p in periods}
eff={p:M[M.period_label==p].effective_from.iloc[0] for p in periods}
events=[]
for i in range(1,len(periods)):
    p0,p1=periods[i-1],periods[i]
    for t in memb[p1]-memb[p0]: events.append((t,eff[p1],'ADD',p1))
    for t in memb[p0]-memb[p1]: events.append((t,eff[p1],'DEL',p1))
E=pd.DataFrame(events,columns=['ticker','edate','kind','period'])
print(f"=== IDX80 reconstitution events, {len(periods)} periods ===")
print(f"  additions {(E.kind=='ADD').sum()}   deletions {(E.kind=='DEL').sum()}   across {E.period.nunique()} rebalances")
print(f"  per rebalance: {E.groupby(['period','kind']).size().unstack(fill_value=0).to_dict('index')}")
px=o.pivot_table(index='date',columns='ticker',values='close')
sess=px.index.sort_values()
uni=px.pct_change().mean(axis=1)          # equal-weight liquid market
def car(tk,d0,a,b):
    if tk not in px.columns: return np.nan
    if d0 not in sess:
        nxt=sess[sess>=d0]
        if not len(nxt): return np.nan
        d0=nxt[0]
    i=sess.get_loc(d0); lo,hi=i+a,i+b
    if lo<0 or hi>=len(sess): return np.nan
    s=px[tk].iloc[lo:hi+1]
    if s.isna().sum()>len(s)*0.3 or s.iloc[0]!=s.iloc[0]: return np.nan
    r=100*(s.iloc[-1]/s.iloc[0]-1)
    m=100*((1+uni.iloc[lo:hi+1]).prod()-1)
    return r-m
print(f"\n{'window':16} {'ADD n':>6} {'ADD CAR%':>9} {'t':>6} | {'DEL n':>6} {'DEL CAR%':>9} {'t':>6}")
for a,b,lab in [(-20,-1,'pre  [-20,-1]'),(-5,-1,'pre  [-5,-1]'),(0,0,'day  [0]'),
                (0,5,'post [0,+5]'),(0,20,'post [0,+20]'),(0,60,'post [0,+60]'),
                (1,20,'post [+1,+20]')]:
    row=[]
    for k in ['ADD','DEL']:
        v=np.array([car(r.ticker,r.edate,a,b) for _,r in E[E.kind==k].iterrows()],float)
        v=v[~np.isnan(v)]
        t=v.mean()/(v.std(ddof=1)/np.sqrt(len(v))) if len(v)>2 else np.nan
        row+= [len(v),v.mean(),t]
    print(f"{lab:16} {row[0]:6} {row[1]:9.2f} {row[2]:6.2f} | {row[3]:6} {row[4]:9.2f} {row[5]:6.2f}")
print("\n  literature: EM inclusions ~+1.89% CAR, deletions ~-3.47%, effect documented as DECAYING")
