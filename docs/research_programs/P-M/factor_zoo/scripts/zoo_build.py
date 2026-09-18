"""Build a wide factor panel from OHLCV. Monthly snapshots, no look-ahead:
every feature at month-end t uses only data up to and including t; the target
is the return from t to t+1 month."""
import sys; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')

with connect(read_only=True) as c:
    df=pd.read_sql("SELECT ticker,date,open,high,low,close,volume FROM ohlcv WHERE is_final=1",c)
    ih=pd.read_sql("SELECT date,close ic FROM ohlcv WHERE ticker='IHSG' AND is_final=1",c)
df['date']=pd.to_datetime(df.date); ih['date']=pd.to_datetime(ih.date)
df=df[(df.close>0)&(df.low>0)&(df.high>=df.low)].sort_values(['ticker','date'])
df=df[df.ticker!='IHSG']
df=df.merge(ih,on='date',how='left')
g=df.groupby('ticker',group_keys=False)
df['ret']=g.close.transform(lambda s:s.pct_change())
df['mret']=df.groupby('date',group_keys=False).ret.transform('mean')   # equal-wt mkt
df['val']=df.close*df.volume
df['adv60']=g.val.transform(lambda s:s.rolling(60,min_periods=60).mean())
df['n']=g.cumcount()+1

# --- features ---
def roll(s,w,f): return s.rolling(w,min_periods=max(10,int(w*0.8))).agg(f)
df['mom12_1']=g.close.transform(lambda s:s.shift(21)/s.shift(252)-1)
df['mom6_1'] =g.close.transform(lambda s:s.shift(21)/s.shift(126)-1)
df['mom3_1'] =g.close.transform(lambda s:s.shift(21)/s.shift(63)-1)
df['mom1']   =g.close.transform(lambda s:s/s.shift(21)-1)
df['rev1w']  =g.close.transform(lambda s:s/s.shift(5)-1)
hl=np.log(df.high/df.low)**2
df['park60']=np.sqrt(hl.groupby(df.ticker).transform(lambda s:s.rolling(60,min_periods=60).mean())/(4*np.log(2)))*np.sqrt(252)*100
df['vol60'] =g.ret.transform(lambda s:s.rolling(60,min_periods=60).std())*np.sqrt(252)*100
df['skew60']=g.ret.transform(lambda s:s.rolling(60,min_periods=60).skew())
df['kurt60']=g.ret.transform(lambda s:s.rolling(60,min_periods=60).kurt())
df['maxret'] =g.ret.transform(lambda s:s.rolling(21,min_periods=15).max())*100
df['minret'] =g.ret.transform(lambda s:s.rolling(21,min_periods=15).min())*100
df['amihud'] =g.apply(lambda x:(x.ret.abs()/x.val).rolling(60,min_periods=40).mean()).reset_index(level=0,drop=True)
df['px']=df.close
df['dollarvol']=df.adv60
df['hi52']=g.close.transform(lambda s:s/s.rolling(252,min_periods=200).max())
df['lo52']=g.close.transform(lambda s:s/s.rolling(252,min_periods=200).min())
df['ma200']=g.close.transform(lambda s:s/s.rolling(200,min_periods=160).mean()-1)
df['ma50'] =g.close.transform(lambda s:s/s.rolling(50,min_periods=40).mean()-1)
df['volshock']=g.volume.transform(lambda s:s.rolling(5,min_periods=5).mean()/s.rolling(60,min_periods=60).mean())
df['illiq_zero']=g.volume.transform(lambda s:(s==0).rolling(60,min_periods=60).mean())
df['volofvol']=g.ret.transform(lambda s:s.rolling(21,min_periods=15).std().rolling(60,min_periods=40).std())*np.sqrt(252)*100
# beta + idio vol vs equal-weight market, 120d -- vectorised rolling cov/var
W=120
cov=g.apply(lambda x:x.ret.rolling(W,min_periods=80).cov(x.mret)).reset_index(level=0,drop=True)
mv =g.apply(lambda x:x.mret.rolling(W,min_periods=80).var()).reset_index(level=0,drop=True)
rv =g.ret.transform(lambda s:s.rolling(W,min_periods=80).var())
df['beta120']=cov/mv
df['ivol120']=np.sqrt((rv-(df.beta120**2)*mv).clip(lower=0))*np.sqrt(252)*100
dcov=g.apply(lambda x:x.ret.where(x.mret<0).rolling(W,min_periods=40).cov(x.mret.where(x.mret<0))).reset_index(level=0,drop=True)
dvar=g.apply(lambda x:x.mret.where(x.mret<0).rolling(W,min_periods=40).var()).reset_index(level=0,drop=True)
df['dnbeta']=dcov/dvar

df['pm']=df.date.dt.to_period('M')
me=df.groupby('pm').date.max()
df['fwd']=g.close.transform(lambda s:s.shift(-21)/s-1)*100
snap=df[df.date.isin(me)].copy().reset_index(drop=True)
snap=snap[(snap.adv60>=1e9)&(snap.close>=50)&(snap.volume>0)&snap.fwd.notna()]
FEATS=['mom12_1','mom6_1','mom3_1','mom1','rev1w','park60','vol60','skew60','kurt60',
       'maxret','minret','amihud','px','dollarvol','hi52','lo52','ma200','ma50',
       'volshock','illiq_zero','volofvol','beta120','ivol120','dnbeta']
snap=snap[['ticker','date','pm','fwd','adv60','close']+FEATS]
snap.to_pickle("/tmp/claude-1000/-home-tjiesar-10-Projects-idx-walkforward-5001/eae2ba9d-2aa0-44ee-b5dd-9ad732c34cb2/scratchpad/zoo.pkl")
print(f"panel: {len(snap):,} name-months, {snap.pm.nunique()} months, {snap.ticker.nunique()} tickers")
print("coverage per feature (% non-null):")
for f in FEATS: print(f"  {f:12} {100*snap[f].notna().mean():5.1f}%")
