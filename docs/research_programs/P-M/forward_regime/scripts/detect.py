import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np
SP=os.environ['SP']

def detect(df, VS=4.0, CP=0.80, RET=0.03, DRY=1.0, W=5,
           RUN=1.15, HOLD=0.92, VDRY=0.50, need_hl=True):
    """Returns entry-level rows. shock at t, absorption t+1..t+W, entry close of t+W."""
    g=df.groupby('ticker',sort=False)
    shock = (df.vol_ratio>=VS)&(df.close_pos>=CP)&(df.ret>=RET)&(df.dry<=DRY)
    out=df.copy()
    out['shock']=shock.fillna(False)
    # forward-window aggregates over t+1..t+W  (computed at t)
    fwd_max_h = g['high'].transform(lambda s: s.shift(-W).rolling(W,min_periods=W).max())
    fwd_min_l = g['low'].transform(lambda s: s.shift(-W).rolling(W,min_periods=W).min())
    fwd_mean_v= g['volume'].transform(lambda s: s.shift(-W).rolling(W,min_periods=W).mean())
    low_first = g['low'].shift(-1); low_last = g['low'].shift(-W)
    out['absorb'] = (
        (fwd_max_h <= out.close*RUN) & (fwd_min_l >= out.close*HOLD) &
        (fwd_mean_v <= out.volume*VDRY)
    )
    if need_hl: out['absorb'] &= (low_last >= low_first)
    out['absorb']=out['absorb'].fillna(False)
    # entry attributes taken from t+W
    for c in ['close','date','f1','f3','f5','f10','f20','m1','m3','m5','m10','m20',
              'bad1','bad3','bad5','bad10','bad20','adv20','n']:
        out['e_'+c]=g[c].shift(-W)
    out['bad_absorb']=g['bad'].transform(lambda s: s.shift(-W).rolling(W,min_periods=1).sum())
    return out

def stats(sub, hs=(1,3,5,10,20), cost=0.006, label=""):
    rows=[]
    for h in hs:
        s=sub[(sub[f'e_bad{h}'].fillna(0)==0)&sub[f'e_f{h}'].notna()]
        if len(s)<5: rows.append((label,h,len(s),*[np.nan]*6)); continue
        raw=s[f'e_f{h}'].values; exc=raw-s[f'm{h}'].values; net=raw-cost
        from panel import cluster_t
        mu,t=cluster_t(exc,s['e_date'].values)
        rows.append((label,h,len(s),s.ticker.nunique(),raw.mean()*100,np.median(raw)*100,
                     net.mean()*100,mu*100,t,(raw>cost).mean()*100))
    return pd.DataFrame(rows,columns=['set','h','N','tk','raw%','med%','net%','exc%','t_clu','win%'])
