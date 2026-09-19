"""GAP 1: ticker -> sector/industry map. The DB has a sector column that is
100% NULL and engine/sector_rotation.py covers 82 of 959 names, which made
sector concentration the largest untestable confound in the program."""
import sys,os,time,json; sys.path.insert(0,".")
import yfinance as yf, pandas as pd, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/zoo.pkl"); tk=sorted(S.ticker.unique())
rows=[];fails=[]
print(f"fetching sector/industry for {len(tk)} tickers",flush=True)
for i,t in enumerate(tk,1):
    try:
        inf=yf.Ticker(f"{t}.JK").info
        rows.append({'ticker':t,'sector':inf.get('sector'),'industry':inf.get('industry'),
                     'country':inf.get('country'),'employees':inf.get('fullTimeEmployees')})
    except Exception as e: fails.append((t,type(e).__name__))
    if i%100==0: print(f"  {i}/{len(tk)} fails={len(fails)}",flush=True)
    time.sleep(0.2)
D=pd.DataFrame(rows); D.to_pickle(f"{SP}/sector_map.pkl")
json.dump(fails,open(f"{SP}/sector_fails.json","w"))
print(f"\nDONE rows={len(D)} fails={len(fails)}")
print(f"  with a sector label : {100*D.sector.notna().mean():.1f}%")
print(f"  distinct sectors    : {D.sector.nunique()}   industries: {D.industry.nunique()}")
print("\n"+D.sector.value_counts(dropna=False).to_string())
