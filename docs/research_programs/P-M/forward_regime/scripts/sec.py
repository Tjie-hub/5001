import os,sys; sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'.')
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SP=os.environ['SP']; pd.set_option('display.width',260)
from engine.sector_rotation import TICKER_SECTOR_MAP as TS
R=pd.read_pickle(f"{SP}/trades.pkl"); R=R[(R.rule=='atr3')&R.mkt.notna()].copy()
R['date']=pd.to_datetime(R.date); R['sec']=R.ticker.map(TS).fillna('UNMAPPED')
print("=== 1. SECTOR COVERAGE of the tested signal set ===")
print("episodes:",len(R)," mapped to a sector:",int((R.sec!='UNMAPPED').sum()),
      "(%.1f%%)"%(100*(R.sec!='UNMAPPED').mean()))
# 2. BETA: is 'excess vs IHSG' just high-beta names in a rising market?
print("\n=== 2. BETA-ADJUSTED ALPHA (regress trade net return on market return over same holding window) ===")
y=R.net.values; x=R.mkt.values
X=np.c_[np.ones(len(x)),x]; b=np.linalg.lstsq(X,y,rcond=None)[0]; e=y-X@b
XtXi=np.linalg.inv(X.T@X); meat=np.zeros((2,2))
for k in pd.unique(R.date.values):
    m=R.date.values==k; s=X[m].T@e[m]; meat+=np.outer(s,s)
V=XtXi@meat@XtXi
print("  alpha = %+.3f%% (t=%.2f)   beta = %.3f (t=%.2f)"%(b[0]*100,b[0]/np.sqrt(V[0,0]),b[1],b[1]/np.sqrt(V[1,1])))
print("  naive 'excess vs IHSG' was +2.26%% -- alpha is what survives beta adjustment")
# 3. SECTOR CONCENTRATION among mapped names: how clustered are concurrent signals?
M=R[R.sec!='UNMAPPED']
if len(M)>100:
    print("\n=== 3. sector mix of signals (mapped subset, N=%d) ==="%len(M))
    vc=M.sec.value_counts(normalize=True)*100
    print(vc.to_string(float_format=lambda x:f"{x:.1f}"))
    print("  top-3 sector share: %.1f%% (equal-weight would be %.1f%%)"%(vc.head(3).sum(),300/len(vc)))
