"""Does higher-frequency rebalancing raise t, or just add autocorrelated noise?
The power ceiling assumed 57 monthly observations. Test weekly/fortnightly
directly, with Newey-West SEs to handle the autocorrelation that faster
rebalancing of a slow signal will induce."""
import sys,os; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
with connect(read_only=True) as c:
    o=pd.read_sql("SELECT ticker,date,high,low,close,volume FROM ohlcv WHERE is_final=1",c)
    CA=pd.read_sql("SELECT ticker,date,value FROM corporate_actions WHERE action='dividend'",c)
o['date']=pd.to_datetime(o.date); CA['date']=pd.to_datetime(CA.date)
o=o[(o.close>0)&(o.low>0)&(o.high>=o.low)].sort_values(['ticker','date']).reset_index(drop=True)
o=o[o.ticker!='IHSG']
g=o.groupby('ticker',group_keys=False)
o['val']=o.close*o.volume
o['adv60']=g.val.transform(lambda s:s.rolling(60,min_periods=60).mean())
hl=np.log(o.high/o.low)**2
o['park60']=np.sqrt(hl.groupby(o.ticker).transform(lambda s:s.rolling(60,min_periods=60).mean())/(4*np.log(2)))*np.sqrt(252)*100
o['zero']=(o.volume==0).astype(int)
o['z_form']=g.zero.transform(lambda s:s.rolling(60,min_periods=60).sum())
# trailing 12m dividend
CAg={t:gg.sort_values('date') for t,gg in CA.groupby('ticker')}
parts=[]
for t,gg in o.groupby('ticker'):
    cg=CAg.get(t)
    if cg is None: parts.append(pd.Series(0.0,index=gg.index)); continue
    d=gg.date.values; dd=cg.date.values; vv=cg.value.values; out=np.zeros(len(gg))
    for i,x in enumerate(d): out[i]=vv[(dd<x)&(dd>=x-np.timedelta64(365,'D'))].sum()
    parts.append(pd.Series(out,index=gg.index))
o['divyield']=100*pd.concat(parts).sort_index()/o.close
px=o[o.volume>0].pivot_table(index='date',columns='ticker',values='close')
sess=px.index.sort_values()
def nw_t(x,lags):
    x=np.asarray(x,float); n=len(x); mu=x.mean(); e=x-mu
    g0=(e@e)/n; s=g0
    for L in range(1,lags+1):
        gl=(e[L:]@e[:-L])/n
        s+= 2*(1-L/(lags+1))*gl
    return mu/np.sqrt(s/n)
def run(step,label):
    days=sess[::step]
    rows=[];prev=set()
    for i in range(len(days)-1):
        d0,d1=days[i],days[i+1]
        snap=o[(o.date==d0)&(o.adv60>=1e9)&(o.close>=50)&(o.volume>0)&o.park60.notna()&(o.z_form==0)]
        if len(snap)<50: continue
        snap=snap[snap.park60<snap.park60.quantile(0.90)]
        sel=snap[snap.divyield>=snap.divyield.quantile(0.80)]
        if len(sel)<10: continue
        nm=list(sel.ticker)
        if d0 not in px.index or d1 not in px.index: continue
        p0=px.loc[d0,nm]; p1=px.loc[d1,nm]; ok=p0.notna()&p1.notna()
        if ok.sum()<8: continue
        r=100*((p1[ok]/p0[ok]).mean()-1)
        u=px.loc[d1,list(snap.ticker)]/px.loc[d0,list(snap.ticker)]
        ur=100*(u.dropna().mean()-1)
        cur=set(np.array(nm)[ok.values]); to=len(cur-prev)/len(cur) if prev else 1.0; prev=cur
        rows.append((d0,r-to*0.60,r-ur,ok.sum(),to))
    B=pd.DataFrame(rows,columns=['d0','net','exc','n','turn'])
    if len(B)<20: print(f"  {label:24} too few ({len(B)})"); return
    yrs=(B.d0.iloc[-1]-B.d0.iloc[0]).days/365.25
    per=len(B)/yrs
    t_iid=B.net.mean()/(B.net.std(ddof=1)/np.sqrt(len(B)))
    L=max(1,int(4*(len(B)/100)**(2/9)))
    t_nw=nw_t(B.net.values,L)
    te=B.exc.mean()/(B.exc.std(ddof=1)/np.sqrt(len(B)))
    ac=pd.Series(B.net).autocorr(1)
    print(f"  {label:24} obs={len(B):4} ({per:5.1f}/yr) turn={B.turn.mean():.2f}  "
          f"NET {100*((1+B.net/100).prod()**(1/yrs)-1):+7.2f}%/yr  t_iid {t_iid:5.2f}  t_NW {t_nw:5.2f}  "
          f"t_exc {te:5.2f}  AC1 {ac:+.2f}")
print("=== does faster rebalancing buy statistical power? ===")
print("   (t_iid assumes independence; t_NW is Newey-West autocorrelation-robust)")
run(21,"monthly  (21 sessions)")
run(10,"fortnightly (10)")
run(5, "weekly   (5)")
run(1, "daily    (1)")
