import os,sys; sys.path.insert(0,os.environ['SP'])
import pandas as pd, numpy as np, sqlite3, warnings; warnings.filterwarnings('ignore')
from panel import cluster_t
SP=os.environ['SP']; pd.set_option('display.width',260); COST=0.006
M=pd.read_pickle(f"{SP}/sweeps.pkl")
con=sqlite3.connect("file:data/walkforward.db?mode=ro",uri=True)
F=pd.read_sql("SELECT ticker,trade_date,net_lot,net_value,buy_freq,sell_freq,composite_score,smart_money "
              "FROM stockbit_flow WHERE trade_date>='2025-01-01'",con)
con.close()
print("daily flow rows 2025+:",len(F),"| tickers",F.ticker.nunique())
F=F.rename(columns={'trade_date':'dstr'})
J=M.merge(F,on=['ticker','dstr'],how='inner')
print("sweeps with same-day flow data:",len(J),"of",int((M.date>='2025-01-01').sum()),"sweeps in the flow era")
def rep(nm,s):
    out=[nm,len(s),s.ticker.nunique()]
    for h in [5,10,20]:
        ss=s[s[f'f{h}'].notna()&s[f'm{h}'].notna()&(s[f'bad{h}'].fillna(1)==0)]
        if len(ss)<60: out+=[np.nan,np.nan]; continue
        mu,t=cluster_t((ss[f'f{h}']-COST-ss[f'm{h}']).values,ss.date.values); out+=[mu*100,t]
    return out
rows=[rep('all sweeps in flow era (no flow filter)',J)]
if 'net_value' in J:
    rows.append(rep('  + net_value > 0 (net buying)',J[J.net_value>0]))
    rows.append(rep('  + net_value top quartile',J[J.net_value>=J.net_value.quantile(.75)]))
if 'composite_score' in J and J.composite_score.notna().any():
    rows.append(rep('  + composite_score >= 70',J[J.composite_score>=70]))
if 'smart_money' in J and J.smart_money.notna().any():
    for v in [x for x in J.smart_money.dropna().unique()][:3]:
        s=J[J.smart_money==v]
        if len(s)>200: rows.append(rep(f'  + smart_money = {v}',s))
print()
print("=== LIQUIDITY SWEEP + ORDER-FLOW CONFIRMATION (2025-01 onward only) ===")
print(pd.DataFrame(rows,columns=['filter','N','tickers','exc5%','t','exc10%','t','exc20%','t']
      ).to_string(index=False,float_format=lambda x:f"{x:.2f}"))
