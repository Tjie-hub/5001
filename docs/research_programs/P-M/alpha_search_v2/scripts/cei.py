"""Composite equity issuance (Daniel-Titman) on the tradeability-conditioned panel.

CEI(tau) = log(MarketCap_t / MarketCap_{t-tau}) - log(cumulative total return over tau)
i.e. the part of market-cap growth NOT explained by price appreciation = net issuance.
Also tested: raw share growth, the cruder version.
Long-only, because IDX restricts shorting.
"""
import sys,os; sys.path.insert(0,".")
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.path.dirname(os.path.abspath(__file__))
S=pd.read_pickle(f"{SP}/trade_panel.pkl")
SH=pd.read_pickle(f"{SP}/fund_shares.pkl")
for d,c in ((S,'date'),(SH,'date')): d[c]=pd.to_datetime(d[c]).astype('datetime64[ns]')
SH=SH.sort_values(['ticker','date'])
S=S.sort_values('date')
S=pd.merge_asof(S,SH.rename(columns={'date':'sd'}).sort_values('sd'),
                left_on='date',right_on='sd',by='ticker',allow_exact_matches=False)
S['mcap']=S.shares*S.close
S=S.sort_values(['ticker','pm'])
g=S.groupby('ticker',group_keys=False)
for tau,lab in [(12,'12m'),(24,'24m')]:
    S[f'lm{tau}']=g.mcap.transform(lambda s:s.shift(tau))
    S[f'lp{tau}']=g.close.transform(lambda s:s.shift(tau))
    S[f'cei{tau}']=np.log(S.mcap/S[f'lm{tau}'])-np.log(S.close/S[f'lp{tau}'])
    S[f'shg{tau}']=np.log(S.shares/g.shares.transform(lambda s:s.shift(tau)))
S=S.replace([np.inf,-np.inf],np.nan)
print(f"panel {len(S):,}  mcap coverage {100*S.mcap.notna().mean():.1f}%  cei12 {100*S.cei12.notna().mean():.1f}%")
def stat(a):
    a=np.asarray(a,float);a=a[~np.isnan(a)];n=len(a)
    if n<3: return np.nan,np.nan,np.nan,n
    return a.mean(),a.mean()/(a.std(ddof=1)/np.sqrt(n)),100*(a>0).mean(),n
def sweep(col,sub,frac=0.20,tgt='fwd'):
    hi,lo,him,lom=[],[],[],[]
    for pm,gg in sub.groupby('pm'):
        gg=gg[gg[col].notna()&gg[tgt].notna()]
        if len(gg)<50: continue
        hq=gg[col].quantile(1-frac); lq=gg[col].quantile(frac)
        H=gg[gg[col]>=hq]; L=gg[gg[col]<=lq]
        if len(H)<8 or len(L)<8: continue
        hi.append(H[tgt].mean()-gg[tgt].mean()); lo.append(L[tgt].mean()-gg[tgt].mean())
        him.append(H[tgt].median()-gg[tgt].median()); lom.append(L[tgt].median()-gg[tgt].median())
    return stat(hi),stat(lo),stat(him),stat(lom)
C=S[S.clean]
print("\n=== COMPOSITE EQUITY ISSUANCE, long-only, CLEAN panel ===")
print("   prediction: HIGH issuance UNDERPERFORMS, LOW issuance outperforms")
print(f"{'measure':10} | {'HIGH mean':>10} {'t':>6} {'HIGH med':>9} {'t':>6} | {'LOW mean':>9} {'t':>6} {'LOW med':>9} {'t':>6}")
for col in ['cei12','cei24','shg12','shg24']:
    h,l,hm,lm=sweep(col,C)
    print(f"{col:10} | {h[0]:10.2f} {h[1]:6.2f} {hm[0]:9.2f} {hm[1]:6.2f} | {l[0]:9.2f} {l[1]:6.2f} {lm[0]:9.2f} {lm[1]:6.2f}")
print("\n=== era split for the best leg ===")
for col in ['cei12','shg12']:
    for lab,sub in [("2021-23",C[C.pm.astype(str).str[:4]<='2023']),("2024-26",C[C.pm.astype(str).str[:4]>='2024']),
                    ("EX-2025",C[C.pm.astype(str).str[:4]!='2025'])]:
        h,l,hm,lm=sweep(col,sub)
        print(f"  {col} {lab:8} LOW-issuance mean {l[0]:+6.2f} (t {l[1]:5.2f})  median {lm[0]:+6.2f} (t {lm[1]:5.2f})  n={l[3]}")

print("\n=== EXCLUSION FORM: drop the high-issuance tail from a long-only book ===")
def overlay(sub,col,frac=0.10,tgt='fwd'):
    out=[]
    for pm,gg in sub.groupby('pm'):
        gg=gg[gg[col].notna()&gg[tgt].notna()]
        if len(gg)<50: continue
        k=gg[gg[col]<gg[col].quantile(1-frac)]
        if len(k)<20: continue
        out.append(k[tgt].mean()-gg[tgt].mean())
    return stat(out)
for frac in [0.05,0.10,0.20,0.30]:
    m,t,p,n=overlay(C,'cei12',frac)
    print(f"  drop top {int(frac*100):2}% issuance   incr {m:+.3f}%/mo  t={t:5.2f}  P>0={p:3.0f}%  n={n}  ->{12*m:+6.2f}%/yr")
print("\n=== does it STACK with volatility exclusion? (both on CLEAN panel) ===")
def combo(sub,cols,frac=0.10,tgt='fwd'):
    out=[]
    for pm,gg in sub.groupby('pm'):
        gg=gg[gg[tgt].notna()]
        for c in cols: gg=gg[gg[c].notna()]
        if len(gg)<50: continue
        k=gg.copy()
        for c in cols: k=k[k[c]<gg[c].quantile(1-frac)]
        if len(k)<20: continue
        out.append(k[tgt].mean()-gg[tgt].mean())
    return stat(out)
for lab,cols in [("vol only",['park60']),("issuance only",['cei12']),("vol + issuance",['park60','cei12'])]:
    m,t,p,n=combo(C,cols)
    print(f"  {lab:18} incr {m:+.3f}%/mo  t={t:5.2f}  P>0={p:3.0f}%  n={n}  ->{12*m:+6.2f}%/yr")
print("\n=== are they independent? correlation of the two exclusion signals ===")
sub=C[C.cei12.notna()&C.park60.notna()]
print(f"  corr(cei12, park60) = {sub.cei12.corr(sub.park60):+.3f}   (rank {sub.cei12.corr(sub.park60,method='spearman'):+.3f})")
print(f"  overlap of the two excluded deciles: ", end="")
ov=[]
for pm,gg in sub.groupby('pm'):
    if len(gg)<50: continue
    a=set(gg[gg.cei12>=gg.cei12.quantile(0.9)].ticker); b=set(gg[gg.park60>=gg.park60.quantile(0.9)].ticker)
    if a and b: ov.append(len(a&b)/len(a))
print(f"{100*np.mean(ov):.1f}%")
