import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, sqlite3, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',260)
BUY,SELL=0.0025,0.0035
S2=pd.read_pickle(f"{SP}/s2.pkl")
S2=S2[S2.date>='2025-01-02'].copy()
S2['dstr']=S2.date.astype(str).str[:10]
print("EP signals in the intraday-data era (2025-01+):",len(S2),"across",S2.ticker.nunique(),"tickers")
con=sqlite3.connect("file:data/walkforward.db?mode=ro",uri=True)
pairs=list(zip(S2.ticker,S2.dstr))
rows=[]
CH=400
for i in range(0,len(pairs),CH):
    ch=pairs[i:i+CH]
    q=("SELECT ticker,trade_date,bar_time,price FROM stockbit_flow_bars WHERE price>0 AND ("
       +" OR ".join(["(ticker=? AND trade_date=?)"]*len(ch))+")")
    rows.append(pd.read_sql(q,con,params=[v for p in ch for v in p]))
con.close()
B=pd.concat(rows,ignore_index=True)
print("intraday bars fetched:",len(B))
B=B[B.bar_time<='15:30']
res=[]
for (tk,ds),x in B.groupby(['ticker','trade_date']):
    x=x.sort_values('bar_time')
    orb=x[x.bar_time<='09:30']
    rest=x[x.bar_time>'09:30']
    if len(orb)<5 or len(rest)<5: continue
    orh=orb.price.max(); lod=x[x.bar_time<='09:30'].price.min()
    br=rest[rest.price>orh]
    if br.empty:
        res.append((tk,ds,np.nan,np.nan,'no_break')); continue
    entry=br.price.iloc[0]; etime=br.bar_time.iloc[0]
    res.append((tk,ds,entry,lod,etime))
R=pd.DataFrame(res,columns=['ticker','dstr','entry','lod','etime'])
print("ORB outcomes:", R.etime.eq('no_break').sum(),"no-break /",len(R),"signals with intraday data")
R=R[R.etime!='no_break'].merge(S2[['ticker','dstr','date','close','f5','f10','f20','m5','m10','m20','bad5','bad10','bad20']],on=['ticker','dstr'])
# return measured from the ACTUAL intraday entry price to the daily close h days later
R['px_close_d0']=R['close']
out=[]
for h in [5,10,20]:
    s=R[R[f'f{h}'].notna()&R[f'm{h}'].notna()&(R[f'bad{h}'].fillna(1)==0)]
    if len(s)<30: continue
    # price at close+h = close_d0 * (1+f_h); return from intraday entry
    ret=(s.px_close_d0*(1+s[f'f{h}']))/s.entry-1-BUY-SELL
    exc=ret-s[f'm{h}']
    mu,t=cluster_t(exc.values,s.date.values)
    out.append((h,len(s),100*ret.mean(),mu*100,t,100*(ret>0).mean()))
print()
print("=== EP with FAITHFUL opening-range-breakout entry (09:00-09:30 OR, buy the break) ===")
print(pd.DataFrame(out,columns=['hold_d','N','net%','excess%','t_clustered','win%']).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
# stop-loss discipline: how often does price fall below LOD (his hard stop) intraday after entry?
print()
print("median entry time after 09:30: %s | median gap entry vs day close: %.2f%%"%(
    sorted(R.etime)[len(R)//2], 100*(R.px_close_d0/R.entry-1).median()))

print()
print("=== era split (intraday era only: 2025-01 onward) ===")
R['yr']=pd.DatetimeIndex(R.date).year
o=[]
for y,gg in R.groupby('yr'):
    s=gg[gg.f20.notna()&gg.m20.notna()&(gg.bad20.fillna(1)==0)]
    if len(s)<30: o.append((y,len(s),np.nan,np.nan,np.nan)); continue
    ret=(s.px_close_d0*(1+s.f20))/s.entry-1-BUY-SELL
    mu,t=cluster_t((ret-s.m20).values,s.date.values)
    o.append((y,len(s),100*ret.mean(),mu*100,t))
print(pd.DataFrame(o,columns=['yr','N','net20%','excess20%','t']).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
print()
print("no-break rate (signal fires but OR never taken out): %.0f%%"%(100*504/864))
