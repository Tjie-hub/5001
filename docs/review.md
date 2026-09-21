Hard data. Here are the key       
  findings:                         
                                    
    ---                             
    Starvation Test Results — 50    
  tickers × 86 days = 4,300 checks  
                                    
    Signal Density (the real        
  starvation)                       
                                    
    ┌─────────────────┬──────────── 
  ─┬──────┬────────────┬─────────── 
  ──┐                               
    │    Strategy     │ Raw Signals 
  │ Rate │ Pass Gates │ Gate Pass   
  % │                               
    ├─────────────────┼──────────── 
  ─┼──────┼────────────┼─────────── 
  ──┤                               
    │ TFB             │ 94          
  │ 2.2% │ 25         │ 27%         
   │                                
    ├─────────────────┼──────────── 
  ─┼──────┼────────────┼─────────── 
  ──┤                               
    │ Liquidity Sweep │ 220         
  │ 5.1% │ 163        │ 74%         
   │                                
    └─────────────────┴──────────── 
  ─┴──────┴────────────┴─────────── 
  ──┘                               
                                    
    95-98% of date×ticker checks    
  produce zero signal of any kind.  
  The fundamental problem           
    isn't gates — it's that these   
  patterns are rare.                
                                    
    The Money Question: Did Gates   
  Block Winners?                    
                                    
    ┌───────────────────────┬────── 
  ───────┬───────────┬───────────── 
  ──┬─────────────┐                 
    │                       │ TFB   
  Blocked │ TFB Gated │ Sweep       
  Blocked │ Sweep Gated │           
    ├───────────────────────┼────── 
  ───────┼───────────┼───────────── 
  ──┼─────────────┤                 
    │ Count                 │ 69    
        │ 25        │ 57            
   │ 163         │                  
    ├───────────────────────┼────── 
  ───────┼───────────┼───────────── 
  ──┼─────────────┤                 
    │ Avg +5d               │ +1.1% 
        │ −8.0%     │ −2.2%         
   │ −0.3%       │                  
    ├───────────────────────┼────── 
  ───────┼───────────┼───────────── 
  ──┼─────────────┤                 
    │ Median +5d            │ −2.2% 
        │ −9.7%     │ −3.6%         
   │ −1.7%       │                  
    ├───────────────────────┼────── 
  ───────┼───────────┼───────────── 
  ──┼─────────────┤                 
    │ % Profitable          │ 41%   
        │ 24%       │ 40%           
   │ 39%         │                  
    ├───────────────────────┼────── 
  ───────┼───────────┼───────────── 
  ──┼─────────────┤                 
    │ Strong winners (>+5%) │ 19    
        │ 1         │ 9             
   │ 23          │                  
    ├───────────────────────┼────── 
  ───────┼───────────┼───────────── 
  ──┼─────────────┤                 
    │ Severe losers (<−5%)  │ 26    
        │ 16        │ 23            
   │ 68          │                  
    └───────────────────────┴────── 
  ───────┴───────────┴───────────── 
  ──┴─────────────┘                 
                                    
    The Gate Failure Breakdown      
  (TFB)                             
                                    
    What kills the 73% of breakouts 
  that get blocked:                 
    - Volume (46%) — VR < 1.8x,     
  most common blocker               
    - Slope (39%) — ma20_slope ≤    
  0.5, second most common           
    - Climax (36%) — vol_ratio ≥    
  4x, anti-blow-off gate            
    - Regime (19%) — close ≤ MA50   
                                    
    Verdict                         
                                    
    ┌────────┬──────────────┬────── 
  ───────────────────────────────── 
  ─────────────────────┐            
    │  Gate  │ Blocked Avg  │       
                     Verdict        
                      │             
    │        │    Return    │       
                                    
                      │             
    ├────────┼──────────────┼────── 
  ───────────────────────────────── 
  ─────────────────────┤            
    │ TFB    │ +1.1% avg    │       
  Borderline — 41% profitable with  
  positive avg, but median  │       
    │ (all   │ but −2.2%    │       
  negative. Skewed by a few big     
  winners. Gated signals       │    
    │ 6)     │ median       │       
  actually underperform (−8% avg).  
  Sample small (94 total).  │       
    ├────────┼──────────────┼────── 
  ───────────────────────────────── 
  ─────────────────────┤            
    │ Sweep  │ −2.2% avg /  │       
  Correct — blocked signals are net 
  losers. Flow gate adds   │        
    │ flow   │ −3.6% median │ +1.9% 
  edge over blocked signals.        
                      │             
    └────────┴──────────────┴────── 
  ───────────────────────────────── 
  ─────────────────────┘            
                                    
    What This Means                 
                                    
    1. The "starvation" diagnosis   
  is correct but the cause is       
  wrong. It's not gates killing 97  
    good trades — it's that 97% of  
  check opportunities produce no    
  pattern at all. These             
    strategies are selective by     
  design.                           
    2. TFB gates are questionable.  
  The blocked signals outperform    
  the gated ones (+1.1% vs          
    −8.0%). The 6 gates might be    
  filtering the wrong dimension —   
  the volume gate (46% of           
    failures) and slope gate (39%)  
  are the biggest offenders. But 94 
  total observations is             
    small — this could be noise.    
    3. Sweep flow gate is           
  validated. Blocked trades lose    
  money. The gate has a real +1.9%  
    edge. Keep it.                  
    4. Even the "good" signals are  
  mediocre. Gated TFB averages −8%, 
  gated Sweep averages              
    −0.3%. Neither has a strong     
  standalone edge. The real value   
  is in the portfolio               
    combination, not individual     
  signal quality.                   
                                    

● This data settles the main
  question and throws up one
  alarming surprise. Let me separate
  the two.

  The starvation hypothesis is
  refuted (as a gate problem)

  This is the headline and it's
  decisive: 95–98% of checks produce
  no signal at all. The doc sold
  the rework as "10 sequential
  filters turn 100 candidates into 3
  trades" — implying gates are
  strangling a rich candidate pool.
  They aren't. The pool is nearly
  empty before any gate runs. TFB
  fires on 2.2% of checks, Sweep on
  5.1%. Loosening gates cannot
  manufacture signals where no
  pattern exists.

  So the doc's central premise —
  increase recall by softening gates
  — is solving a problem you don't
  have. If you want more trades, you
  add more validated detectors /
  wider universe / better flow
  coverage, not softer thresholds.
  That's the Phase-1-vs-Phase-2
  split I flagged, now with evidence
  behind it.

  The surprise: TFB gates appear to
  select losers — and that
  contradicts your own WF record

  This is the part I would not
  accept at face value, in either
  direction:

  Gated TFB
  This test (raw fwd return): −8.0%
  avg,
     24%  profitable
  Memory
  (project_tfb_context_filter, WF
  OOS): consistency
    40.7%, avg P&L  +4.63%
  ──────────────────────────────────
  ─
  Effect of gates
  This test (raw fwd return): gates
  pick
    the worse  cohort
  Memory
  (project_tfb_context_filter, WF
  OOS): gates
    improved OOS materially

  These two cannot both be true as
  stated. Before anyone touches the
  TFB gates, that contradiction has
  to be reconciled. The most likely
  culprit is the measurement, not
  the gates:

  1. Raw +5/10/20d ≠ the strategy's
  realized P&L. TFB is a breakout —
  it's designed for a negative
  median and positive mean (cut
  losers fast, let winners run).
  Judging it by median or
  %-profitable on a fixed horizon
  penalizes exactly the right-skewed
  payoff it's built for. The WF
  result uses the strategy's actual
  stop/target/time-stop; this test
  uses a naive hold. Those measure
  different things. A stop truncates
  the −9.7% median tail that's
  dragging the gated cohort here.
  2. n = 25 gated TFB is too small
  to overturn a WF result. 16 severe
  losers out of 25 over one 86-day
  window is very possibly a
  single-regime artifact. The WF
  test spanned more history and more
  folds.
  3. If these 86 days were in-sample
  for the gate tuning, in-sample
  should look good — it looks
  terrible — which argues against
  "the gates were overfit" and
  toward "the metric is wrong" or
  "this window is unrepresentative."

  So my read on the paste's verdict
  "TFB gates are questionable":
  plausible but unproven, and most
  likely a metric artifact. Don't
  rip them out on n=25 raw-return.
  The decisive follow-up is cheap:

  ▎ Re-run the same 94 TFB signals
  ▎ (blocked + gated) but score each
  ▎ with the strategy's actual exit
  ▎ logic (stop / target /
  ▎ time-stop), not fixed +5/10/20d.
  ▎ If gated still underperforms
  ▎ blocked under real exits, the
  ▎ gates are genuinely inverted and
  ▎ we investigate the volume+slope
  ▎ thresholds. If gated flips to
  ▎ outperform, the WF result holds
  ▎ and the doc's "soften TFB gates"
  ▎ idea is dead.

  What's settled regardless

  - Sweep flow gate: keep it.
  Blocked trades lose money (−2.2%
  avg), +1.9% edge. Consistent with
  the WF record. The doc's "make
  flow a soft score" idea is refuted
  for Sweep.
  - Individual signals are mediocre
  across the board (gated Sweep
  −0.3%, gated TFB negative). This
  is the real finding: the edge, if
  any, lives at the portfolio level,
  not in single signals. That is a
  direct argument for building the
  ranking/allocation layer (Phase 1)
  and against dissolving the
  per-signal gates (Phase 2).

  Net verdict on the doc

  The empirics flip the doc's
  recommendation: build the ranking
  layer (it's where the only
  plausible edge is), and keep the
  gates — starvation isn't caused by
  them. The one open question is
  whether TFB's specific gates are
  inverted, and that's a measurement
  bug until proven otherwise.

  Want me to write that exit-aware
  re-run of the 94 TFB signals? It's
  the one test that converts
  "questionable" into a decision