import os,sys; sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'.')
import pandas as pd, numpy as np, warnings, collections; warnings.filterwarnings('ignore')
exec(open(os.environ['SP']+'/port.py').read().split("def curve")[0])
PANEL_END=pd.Timestamp(cal.max())
last_bar=d.groupby('ticker').date.max()
# classify the last-bar exits
P['ext']=pd.to_datetime(P.ext); P['ent']=pd.to_datetime(P.ent)
P['tick_last']=P.ticker.map(last_bar)
P['at_last']=P.ext>=P.tick_last
LB=P[P.at_last]
LB=LB.assign(gap_days=(PANEL_END-LB.tick_last).dt.days)
print("positions exiting at ticker's last bar:",len(LB))
print("  still open at panel end (last bar within 10d of %s): %d"%(PANEL_END.date(),(LB.gap_days<=14).sum()))
print("  ticker data ENDS EARLY (likely delist/suspend):        %d"%((LB.gap_days>14).sum()))
DL=LB[LB.gap_days>14]
print("\n  affected tickers:",DL.ticker.nunique(),"| example:",DL.groupby('ticker').tick_last.first().sort_values().head(6).to_dict())
# --- gap check: long suspensions INSIDE a holding period ---
gaps=[]
for tk,x in d.groupby('ticker',sort=False):
    dt=pd.to_datetime(pd.Series(x.date.values))
    gp=dt.diff().dt.days
    big=dt[gp>30]
    for b in big: gaps.append((tk,b))
G=pd.DataFrame(gaps,columns=['ticker','resume'])
print("\ntrading gaps >30 calendar days in the corpus:",len(G),"across",G.ticker.nunique(),"tickers")
hit=0
for tk,a,b in P[['ticker','ent','ext']].itertuples(index=False):
    gg=G[(G.ticker==tk)&(G.resume>a)&(G.resume<=b)]
    if len(gg): hit+=1
print("positions whose holding window SPANS such a gap:",hit,"(%.2f%% of %d)"%(100*hit/len(P),len(P)))
