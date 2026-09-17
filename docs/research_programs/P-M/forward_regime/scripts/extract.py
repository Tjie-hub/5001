import sqlite3, pandas as pd, numpy as np, os
SP = os.environ['SP']
con = sqlite3.connect("file:data/walkforward.db?mode=ro", uri=True)
df = pd.read_sql("SELECT ticker,date,open,high,low,close,volume FROM ohlcv WHERE is_final=1 AND close>0 AND volume>=0", con)
ca = pd.read_sql("SELECT ticker,date,action,value FROM corporate_actions", con)
con.close()
df['date']=pd.to_datetime(df['date'])
df=df.sort_values(['ticker','date']).reset_index(drop=True)
print("rows",len(df),"tickers",df.ticker.nunique(),"span",df.date.min().date(),df.date.max().date())
print("CA:",len(ca), ca.action.value_counts().to_dict())
df.to_pickle(f"{SP}/ohlcv.pkl")
ca.to_pickle(f"{SP}/ca.pkl")
