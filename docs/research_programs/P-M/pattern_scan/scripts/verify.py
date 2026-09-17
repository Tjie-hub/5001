import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.environ['SP']; pd.set_option('display.width',260)
d=pd.read_pickle(f"{SP}/panel2.pkl")
d=d[d.ticker=='BRPT'].sort_values('date').reset_index(drop=True)
c=d.close;h=d.high;l=d.low
d['lo20']=l.rolling(20,min_periods=20).min().shift(1)
d['hi20']=h.rolling(20,min_periods=20).max().shift(1)
d['ema10']=c.ewm(span=10,adjust=False,min_periods=10).mean()
d['ema20_']=c.ewm(span=20,adjust=False,min_periods=20).mean()
d['dstr']=d.date.astype(str).str[:10]
print("=== FAILED BREAKDOWN 2026-03-17: does it match the definition? ===")
i=d.index[d.dstr=='2026-03-17'][0]
x=d.loc[i-3:i+2,['dstr','open','high','low','close','lo20']]
print(x.to_string(index=False,float_format=lambda v:f"{v:.0f}"))
r=d.loc[i]
print(f"  rule: low({r.low:.0f}) < lo20({r.lo20:.0f}) = {r.low<r.lo20} ; close({r.close:.0f}) > lo20 = {r.close>r.lo20}")
print(f"  -> genuine sweep of the 20d low with a close back inside: {(r.low<r.lo20) and (r.close>r.lo20)}")
print()
print("=== WEDGE POP 2026-04-07: are the prior 20 bars really a converging wedge? ===")
j=d.index[d.dstr=='2026-04-07'][0]
w=d.loc[j-20:j-1]
def sl(s):
    x=np.arange(len(s)); return np.polyfit(x,s.values,1)[0]
sh=sl(w.high); slo=sl(w.low)
print(f"  slope of HIGHS over prior 20 bars : {sh:+.2f} /bar")
print(f"  slope of LOWS  over prior 20 bars : {slo:+.2f} /bar")
print(f"  both falling? {sh<0 and slo<0} | converging (highs fall faster)? {sh<slo}")
print(f"  range first 5 bars: {w.high[:5].max()-w.low[:5].min():.0f}  last 5 bars: {w.high[-5:].max()-w.low[-5:].min():.0f}  -> contracting? {(w.high[-5:].max()-w.low[-5:].min())<(w.high[:5].max()-w.low[:5].min())}")
rr=d.loc[j]
print(f"  trigger: close({rr.close:.0f}) > ema10({rr.ema10:.0f}) = {rr.close>rr.ema10}; prior close below ema10 = {d.loc[j-1,'close']<=d.loc[j-1,'ema10']}")
print()
print("  bars (prior 20 + signal):")
print(d.loc[j-20:j,['dstr','high','low','close','ema10']].to_string(index=False,float_format=lambda v:f"{v:.0f}"))
