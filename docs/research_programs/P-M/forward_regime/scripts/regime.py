import os,sys; sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'.')
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from engine.regime_filter import detect_regime
SP=os.environ['SP']; pd.set_option('display.width',250)
raw=pd.read_pickle(f"{SP}/ohlcv.pkl")
ih=raw[raw.ticker=='IHSG'].sort_values('date').reset_index(drop=True)
lab=[]
for i in range(len(ih)):
    if i<60: lab.append(None); continue
    lab.append(detect_regime(ih.iloc[max(0,i-120):i+1][['date','open','high','low','close','volume']].copy()))
ih['regime']=lab
ih=ih[ih.regime.notna()].reset_index(drop=True)
# episodes
ih['blk']=(ih.regime!=ih.regime.shift()).cumsum()
ep=ih.groupby('blk').agg(regime=('regime','first'),start=('date','first'),end=('date','last'),
                         n=('date','size'),px0=('close','first'),px1=('close','last')).reset_index(drop=True)
ep['ret%']=100*(ep.px1/ep.px0-1)
ep=ep[ep.n>=5]
print("=== IHSG regime episodes (production detect_regime), >=5 sessions ===")
print(ep[['regime','start','end','n','ret%']].to_string(index=False,
      formatters={'start':lambda x:str(x)[:10],'end':lambda x:str(x)[:10],'ret%':'{:+.1f}'.format}))
print()
print("episode counts:", ep.regime.value_counts().to_dict())
print("session counts:", ih.regime.value_counts().to_dict())
print()
print("=== 2026 month by month ===")
ih['ym']=ih.date.dt.to_period('M')
m=ih[ih.date>='2025-10-01'].groupby('ym').agg(regime=('regime',lambda s:s.value_counts().index[0]),
      close=('close','last'),n=('close','size'))
m['mret%']=100*(m.close/m.close.shift(1)-1)
print(m.to_string(float_format=lambda x:f"{x:.1f}"))
ih[['date','regime']].to_pickle(f"{SP}/ihsg_regime.pkl")
