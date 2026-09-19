"""EXTENDED PANEL 2005-2026: combine the pre-2021 backfill with the settled DB
corpus, back-adjust splits, rebuild features, apply tradeability conditioning,
and attach sector labels.

Split handling: raw prices carry split discontinuities. Each ticker's series is
divided by the CUMULATIVE PRODUCT of all split ratios effective AFTER each date,
which puts the whole history on today's share basis. Volume is scaled inversely.
"""
import sys,os; sys.path.insert(0,".")
from data.db import connect
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
H=pd.read_pickle(f"{SP}/hist_pre2021.pkl")
with connect(read_only=True) as c:
    D=pd.read_sql("SELECT ticker,date,open,high,low,close,volume FROM ohlcv WHERE is_final=1",c)
D['date']=pd.to_datetime(D.date); H['date']=pd.to_datetime(H.date)
D=D[D.ticker!='IHSG']
H=H[['ticker','date','open','high','low','close','volume']]
D=D[['ticker','date','open','high','low','close','volume']]
O=pd.concat([H,D],ignore_index=True).drop_duplicates(['ticker','date'],keep='last')
O=O[(O.close>0)&(O.low>0)&(O.high>=O.low)].sort_values(['ticker','date']).reset_index(drop=True)
print(f"combined: {len(O):,} bars  {O.ticker.nunique()} tickers  {O.date.min().date()} -> {O.date.max().date()}")

# ---- split back-adjustment ----
SPL=pd.read_pickle(f"{SP}/split_hist.pkl") if os.path.exists(f"{SP}/split_hist.pkl") else pd.DataFrame()
if len(SPL):
    SPL=SPL[SPL.ratio>0].sort_values(['ticker','date'])
    # cumulative product of splits occurring ON OR AFTER each bar, per ticker,
    # computed by reverse cumprod over merged split events (no python loop)
    ev=SPL.rename(columns={'date':'sdate'})[['ticker','sdate','ratio']]
    O=O.sort_values(['ticker','date'])
    fac=np.ones(len(O),dtype='float32')
    pos={t:i for i,t in enumerate(O.ticker.values)}   # first index per ticker
    idx_by_t=O.groupby('ticker',sort=False).indices
    for t,rows_ in ev.groupby('ticker',sort=False):
        ii=idx_by_t.get(t)
        if ii is None: continue
        dts=O.date.values[ii]
        f=np.ones(len(ii),dtype='float32')
        for sd,rt in zip(rows_.sdate.values,rows_.ratio.values):
            f[dts<sd]*=rt
        # ONLY the pre-2021 backfill is on an as-traded basis. The settled DB
        # corpus is already back-adjusted to today's share basis (verified: no
        # price jump at BBCA/HEAL/GOOD split dates), so adjusting it again would
        # double-count every post-2021 split.
        f[dts>=np.datetime64('2021-07-05')]=1.0
        fac[ii]=f
    for c_ in ['open','high','low','close']:
        O[c_]=(O[c_].astype('float32')/fac)
    O['volume']=O.volume.astype('float64')*fac
    del fac
    print(f"  split-adjusted using {len(SPL):,} events on {SPL.ticker.nunique()} tickers")
else:
    print("  !! split history missing -- NOT adjusted")

for c_ in ['open','high','low','close']: O[c_]=O[c_].astype('float32')
g=O.groupby('ticker',group_keys=False)
O['ret']=g.close.transform(lambda s:s.pct_change()).astype('float32')
ext=((O.ret<-0.45)|(O.ret>1.5)).sum()
print(f"  residual extreme moves after adjustment: {ext} ({100*ext/len(O):.4f}%)")

O['val']=O.close*O.volume
O['adv60']=g.val.transform(lambda s:s.rolling(60,min_periods=60).mean())
hl=np.log(O.high/O.low)**2
O['park60']=np.sqrt(hl.groupby(O.ticker).transform(lambda s:s.rolling(60,min_periods=60).mean())/(4*np.log(2)))*np.sqrt(252)*100
O['zero']=(O.volume<=0).astype(int)
O['z_form']=g.zero.transform(lambda s:s.rolling(60,min_periods=60).sum())
O['z_fwd']=g.zero.transform(lambda s:s[::-1].rolling(21,min_periods=1).sum()[::-1].shift(-1))
O['fwd']=g.close.transform(lambda s:s.shift(-21)/s-1)*100
O['pm']=O.date.dt.to_period('M')
me=O.groupby('pm').date.max()
S=O[O.date.isin(me)].copy()
S=S[(S.adv60>=1e9)&(S.close>=50)&(S.volume>0)&S.park60.notna()&S.fwd.notna()]
S['clean']=(S.z_form.fillna(0)==0)&(S.z_fwd.fillna(0)==0)

# dividends over the whole span
DH=pd.read_pickle(f"{SP}/div_hist.pkl") if os.path.exists(f"{SP}/div_hist.pkl") else pd.DataFrame()
if len(DH):
    DH['date']=pd.to_datetime(DH.date)
    # NOTE: source dividends are ALREADY split-adjusted to today's basis --
    # verified on 54 splits with dividends either side: observed pre/post DPS
    # ratio median 0.70 against a median split ratio of 3.66, correlation -0.099.
    # They must therefore NOT be adjusted again.
    CAg={t:gg.sort_values('date') for t,gg in DH.groupby('ticker')}
    parts=[]
    for t,gg in S.groupby('ticker'):
        cg=CAg.get(t)
        if cg is None: parts.append(pd.Series(0.0,index=gg.index)); continue
        d=gg.date.values; dd=cg.date.values; vv=cg.value.values; out=np.zeros(len(gg))
        for i,x in enumerate(d): out[i]=vv[(dd<x)&(dd>=x-np.timedelta64(365,'D'))].sum()
        parts.append(pd.Series(out,index=gg.index))
    S['dps12']=pd.concat(parts).sort_index()
    S['divyield']=100*S.dps12/S.close
    print(f"  dividend history: {len(DH):,} events, pre-2021 {int((DH.date<pd.Timestamp('2021-07-05')).sum()):,}")
else:
    S['divyield']=np.nan; print("  !! dividend history missing")

SEC=pd.read_pickle(f"{SP}/sector_map.pkl")
S=S.merge(SEC[['ticker','sector']],on='ticker',how='left')
S.to_pickle(f"{SP}/ext_panel.pkl")
print(f"\nEXTENDED PANEL: {len(S):,} name-months  {S.pm.nunique()} months  {S.ticker.nunique()} tickers")
print(f"  span {S.date.min().date()} -> {S.date.max().date()}  ({(S.date.max()-S.date.min()).days/365.25:.1f} years)")
print(f"  clean {100*S.clean.mean():.1f}%   sector-labelled {100*S.sector.notna().mean():.1f}%   divyield {100*S.divyield.notna().mean():.1f}%")
print("\n  names per month by era:")
for y,gg in S.groupby(S.pm.astype(str).str[:4]):
    if int(y)%3==0 or int(y)>=2020: print(f"    {y}  {gg.groupby('pm').size().mean():5.0f}")
