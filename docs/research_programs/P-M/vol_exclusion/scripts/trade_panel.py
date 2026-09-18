"""Tradeability-conditioned panel for the volatility re-run.

Three independent contamination flags, because they act through different
mechanisms and must not be conflated:
  frz_form : zero-volume session inside the 60-day FORMATION window
             -> the volatility estimate itself is built on untradeable prints
  frz_fwd  : zero-volume session inside the 21-session FORWARD window
             -> the return could not have been earned (cannot hold or exit)
  susp     : ticker/date inside a suspension_events episode
"""
import sys,os; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
with connect(read_only=True) as c:
    o=pd.read_sql("SELECT ticker,date,open,high,low,close,volume FROM ohlcv WHERE is_final=1",c)
    SU=pd.read_sql("SELECT ticker,last_normal_date,resume_date,classification FROM suspension_events",c)
o['date']=pd.to_datetime(o.date)
o=o[(o.close>0)&(o.low>0)&(o.high>=o.low)].sort_values(['ticker','date']).reset_index(drop=True)
o=o[o.ticker!='IHSG']
g=o.groupby('ticker',group_keys=False)
o['val']=o.close*o.volume
o['adv60']=g.val.transform(lambda s:s.rolling(60,min_periods=60).mean())
hl=np.log(o.high/o.low)**2
o['park60']=np.sqrt(hl.groupby(o.ticker).transform(lambda s:s.rolling(60,min_periods=60).mean())/(4*np.log(2)))*np.sqrt(252)*100
o['ret']=g.close.transform(lambda s:s.pct_change())
o['vol60']=g.ret.transform(lambda s:s.rolling(60,min_periods=60).std())*np.sqrt(252)*100
o['zero']=(o.volume==0).astype(int)
o['z_form']=g.zero.transform(lambda s:s.rolling(60,min_periods=60).sum())
o['z_fwd'] =g.zero.transform(lambda s:s[::-1].rolling(21,min_periods=1).sum()[::-1].shift(-1))
o['flat']  =(o.high==o.low).astype(int)
o['flat_form']=g.flat.transform(lambda s:s.rolling(60,min_periods=60).sum())
o['fwd']=g.close.transform(lambda s:s.shift(-21)/s-1)*100
# tradeable-price forward return: exit only on a volume>0 print
o['cl_t']=o.close.where(o.volume>0)
o['fwd_t']=g.cl_t.transform(lambda s:s.shift(-21))/o.cl_t*100-100
o['pm']=o.date.dt.to_period('M')
me=o.groupby('pm').date.max()
S=o[o.date.isin(me)].copy()
S=S[(S.adv60>=1e9)&(S.close>=50)&(S.volume>0)&S.park60.notna()]
# suspension overlay
SU['last_normal_date']=pd.to_datetime(SU.last_normal_date); SU['resume_date']=pd.to_datetime(SU.resume_date)
S['susp']=False
for _,r in SU.dropna(subset=['resume_date']).iterrows():
    m=(S.ticker==r.ticker)&(S.date>=r.last_normal_date)&(S.date<=r.resume_date)
    S.loc[m,'susp']=True
S['frz_form']=S.z_form.fillna(0)>0
S['frz_fwd'] =S.z_fwd.fillna(0)>0
S['clean']   =~S.frz_form & ~S.frz_fwd & ~S.susp
S.to_pickle(f"{SP}/trade_panel.pkl")
print(f"panel: {len(S):,} name-months, {S.pm.nunique()} months")
print(f"  frz_form (zero-vol in formation) : {100*S.frz_form.mean():5.2f}%")
print(f"  frz_fwd  (zero-vol in forward)   : {100*S.frz_fwd.mean():5.2f}%")
print(f"  susp     (in suspension episode) : {100*S.susp.mean():5.2f}%")
print(f"  CLEAN    (none of the above)     : {100*S.clean.mean():5.2f}%")
print(f"\n=== does contamination CREATE high measured volatility? ===")
S['vd']=S.groupby('pm',group_keys=False).park60.transform(lambda s:pd.qcut(s,10,labels=False,duplicates='drop'))
for k in [0,4,8,9]:
    d=S[S.vd==k]
    print(f"  park60 D{k+1:<2} frz_form {100*d.frz_form.mean():5.2f}%  frz_fwd {100*d.frz_fwd.mean():5.2f}%  "
          f"susp {100*d.susp.mean():5.2f}%  flat days/60 {d.flat_form.mean():5.1f}  median park60 {d.park60.median():6.1f}")
