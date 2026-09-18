import os,sys; sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'.')
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from engine.regime_filter import detect_regime
from engine.indicators import calc_adx
SP=os.environ['SP']; pd.set_option('display.width',260)
raw=pd.read_pickle(f"{SP}/ohlcv.pkl"); ih=raw[raw.ticker=='IHSG'].sort_values('date').reset_index(drop=True)

def ma_slope(df,ma,lb):
    m=df.close.rolling(ma).mean()
    return 100*(m/m.shift(lb)-1)

def fast_regime(df, adx_n=7, ma=10, lb=3, thr=1.0):
    """SHORT tier: the SAME BULL/BEAR/SIDEWAYS logic as detect_regime, faster
    parameters. Explicitly a research variant, not the frozen production fn."""
    if len(df)<max(adx_n,ma)+lb+2: return 'SIDEWAYS'
    a=calc_adx(df,adx_n).iloc[-1]; s=ma_slope(df,ma,lb).iloc[-1]
    if pd.isna(a) or pd.isna(s): return 'SIDEWAYS'
    if a>25 and s>thr: return 'BULL'
    if a>25 and s<-thr: return 'BEAR'
    return 'SIDEWAYS'

# MID = production detect_regime on daily
mid=[]; short=[]
for i in range(len(ih)):
    w=ih.iloc[max(0,i-120):i+1]
    mid.append(detect_regime(w.copy()) if i>=60 else None)
    short.append(fast_regime(w.copy()) if i>=60 else None)
ih['MID']=mid; ih['SHORT']=short
# LONG = detect_regime on weekly bars, last CLOSED week before the date
W=ih.set_index('date').resample('W-FRI').agg(open=('open','first'),high=('high','max'),
    low=('low','min'),close=('close','last'),volume=('volume','sum')).dropna().reset_index()
wl=[]
for i in range(len(W)):
    wl.append(detect_regime(W.iloc[max(0,i-60):i+1].copy()) if i>=30 else None)
W['LONG']=wl
wk=[(d,r) for d,r in zip(W.date,W.LONG) if r]
def long_at(t):
    p=[r for d,r in wk if d<t]
    return p[-1] if p else None
ih['LONG']=[long_at(t) for t in ih.date]
S=ih[['date','LONG','MID','SHORT']].dropna()
print("dated states:",len(S),S.date.min().date(),'->',S.date.max().date())
for c in ['LONG','MID','SHORT']:
    print(f"  {c:6s}",S[c].value_counts().to_dict())
S.to_pickle(f"{SP}/tiers.pkl")
print()
print("current state:",S.iloc[-1].to_dict())
