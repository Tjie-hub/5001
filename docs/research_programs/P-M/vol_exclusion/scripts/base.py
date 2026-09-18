import sys; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np
def panel():
    with connect(read_only=True) as c:
        df=pd.read_sql("SELECT ticker,date,open,high,low,close,volume FROM ohlcv WHERE is_final=1",c)
    df['date']=pd.to_datetime(df.date); df=df.sort_values(['ticker','date']).reset_index(drop=True)
    df=df[(df.volume>0)&(df.close>0)&(df.low>0)&(df.high>=df.low)]
    df['val']=df.close*df.volume
    g=df.groupby('ticker',group_keys=False)
    df['adv60']=g.val.transform(lambda s:s.rolling(60,min_periods=60).mean())
    hl=np.log(df.high/df.low)**2
    p=hl.groupby(df.ticker).transform(lambda s:s.rolling(60,min_periods=60).mean())
    df['park60']=np.sqrt(p/(4*np.log(2)))*np.sqrt(252)*100
    df['cc60']=g.close.transform(lambda s:s.pct_change().rolling(60,min_periods=60).std())*np.sqrt(252)*100
    df['fwd_m']=g.close.transform(lambda s:s.shift(-21)/s-1)*100
    df['pm']=df.date.dt.to_period('M')
    return df
def month_ends(df):
    return df.groupby('pm').date.max()
def snapshots(df,advmin=1e9,pxmin=50):
    me=month_ends(df); s=df[df.date.isin(me)]
    return s[(s.adv60>=advmin)&(s.close>=pxmin)&s.park60.notna()&s.fwd_m.notna()&(s.volume>0)].copy()
def stat(inc):
    inc=np.asarray(inc,float); n=len(inc)
    t=inc.mean()/(inc.std(ddof=1)/np.sqrt(n)) if n>1 else np.nan
    return inc.mean(),t,100*(inc>0).mean(),n
