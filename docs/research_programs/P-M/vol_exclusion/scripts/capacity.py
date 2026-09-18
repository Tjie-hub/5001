import sys; sys.path.insert(0,".")
import numpy as np, pandas as pd
pd.set_option('display.width',200)

# measured in impact.py
BAND = {   # label: (avg ADV Rp bn, CS spread %, Amihud % per Rp 1bn traded)
 'least-liquid 200 (Rp1-4bn)': (2.2, 0.830, 1.07),
 'live spec top-200 (Rp>4bn)': (18.0, 0.730, 0.15),
}
EDGE = {   # gross incremental, %/yr
 'least-liquid 200 (Rp1-4bn)': 3.57,
 'live spec top-200 (Rp>4bn)': 1.92,   # 2025-26 run-rate, the honest forward number
}
TURN_M = 0.13            # monthly one-way turnover
ANN_TRADED = 2*TURN_M*12 # both sides, annualised, as a multiple of AUM
N = 200

print(f"assumptions: {N} names, {TURN_M:.0%}/mo one-way turnover -> {ANN_TRADED:.2f}x AUM traded/yr\n")
for lab,(adv,spr,ami) in BAND.items():
    edge=EDGE[lab]
    print(f"=== {lab} ===  gross edge {edge:+.2f}%/yr, avg ADV Rp {adv:.1f}bn, "
          f"spread {spr:.2f}%, Amihud {ami:.2f}%/Rp1bn")
    rows=[]
    for aum_bn in [10,25,50,100,200,400,800]:
        pos=aum_bn/N                       # Rp bn per position
        impact=ami*pos                     # one-way, linear
        one_way=spr/2+impact
        drag=ANN_TRADED*one_way
        part=100*pos/adv                   # % of one day's ADV per trade
        rows.append((aum_bn,pos*1000,part,spr/2,impact,one_way,drag,edge-drag))
    R=pd.DataFrame(rows,columns=['AUM Rp bn','pos Rp m','% of ADV','½spread%',
                                 'impact%','1-way%','drag %/yr','NET %/yr'])
    print(R.to_string(index=False,float_format=lambda x:f"{x:.2f}"))
    # breakeven
    be_oneway=edge/ANN_TRADED
    be_impact=be_oneway-spr/2
    be_aum=N*be_impact/ami if be_impact>0 else 0
    print(f"  -> breakeven AUM ~ Rp {be_aum:,.0f}bn "
          f"(US$ {be_aum/16.5:,.1f}m at 16,500)   [one-way budget {be_oneway:.2f}%]\n")
