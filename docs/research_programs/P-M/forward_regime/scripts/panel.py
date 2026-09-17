import pandas as pd, numpy as np, os
SP=os.environ['SP']
RT_COST = 0.0015+0.0010+0.0025+0.0010   # buy comm+slip + sell comm+slip = 0.60%

def build():
    df = pd.read_pickle(f"{SP}/ohlcv.pkl")
    ca = pd.read_pickle(f"{SP}/ca.pkl")
    g = df.groupby('ticker', sort=False)
    df['ret']      = g['close'].pct_change()
    df['pc']       = g['close'].shift(1)
    df['v20']      = g['volume'].transform(lambda s: s.rolling(20,min_periods=15).mean()).groupby(df.ticker).shift(1)
    df['v5']       = g['volume'].transform(lambda s: s.rolling(5,min_periods=4).mean()).groupby(df.ticker).shift(1)
    df['adv20']    = g.apply(lambda x: (x.close*x.volume).rolling(20,min_periods=15).mean(), include_groups=False).reset_index(level=0,drop=True)
    df['adv20']    = df.groupby('ticker',sort=False)['adv20'].shift(1)
    rng = (df.high-df.low).replace(0,np.nan)
    df['close_pos'] = (df.close-df.low)/rng
    df['vol_ratio'] = df.volume/df.v20.replace(0,np.nan)
    df['dry']       = df.v5/df.v20.replace(0,np.nan)
    df['n']         = g.cumcount()

    # --- contamination guards ---
    splits = ca[ca.action=='split'][['ticker','date']].copy()
    splits['date']=pd.to_datetime(splits['date']); splits['is_split']=1
    df = df.merge(splits, on=['ticker','date'], how='left')
    df['is_split']=df['is_split'].fillna(0)
    # unadjusted-CA fingerprint: a single day move beyond IDX auto-reject bounds
    df['bad'] = ((df.ret.abs()>0.35) | (df.is_split>0)).astype(int)
    return df

def add_fwd(df, hs):
    g=df.groupby('ticker',sort=False)
    for h in hs:
        df[f'f{h}'] = g['close'].shift(-h)/df['close'] - 1
        # contamination inside the forward window
        df[f'bad{h}'] = g['bad'].transform(lambda s: s.shift(-1).rolling(h,min_periods=1).sum()[::1]).values
    return df

def market(df, liq):
    m = df[liq].groupby('date')['ret'].median()
    idx = (1+m.fillna(0)).cumprod()
    return idx

def cluster_t(x, groups):
    """one-way cluster-robust t-stat of the mean, clustered on `groups`."""
    x=np.asarray(x,float); groups=np.asarray(groups)
    n=len(x)
    if n<3: return np.nan, np.nan
    mu=x.mean(); e=x-mu
    s=pd.Series(e).groupby(groups).sum().values
    G=len(s)
    if G<3: return mu, np.nan
    var = (s**2).sum()*(G/(G-1))/n**2
    if var<=0: return mu, np.nan
    return mu, mu/np.sqrt(var)
