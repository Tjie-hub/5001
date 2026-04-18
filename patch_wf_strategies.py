#!/usr/bin/env python3
import shutil
from datetime import datetime

WF_FILE = 'engine/walkforward_multi.py'
shutil.copy2(WF_FILE, f'{WF_FILE}.new_strat_{datetime.now().strftime("%Y%m%d_%H%M%S")}')

OLD_FUNCS = """STRATEGY_FUNCS = {
    'Momentum Following':      strategy_momentum,
    'Volume Profile POC':      strategy_volume_profile_poc,
    'Inside Bar Breakout':     strategy_inside_bar_breakout,
    'NR7 Breakout':            strategy_nr7_breakout,
    'Regime Adaptive':         strategy_regime_adaptive,
    'ORB':                      strategy_orb,
}"""

NEW_FUNCS = """STRATEGY_FUNCS = {
    'vol_weighted':            strategy_vol_weighted,
    'momentum':                strategy_momentum,
    'vwap_reversion':          strategy_vwap_reversion,
    'conservative':            strategy_conservative,
    'Volume Profile POC':      strategy_volume_profile_poc,
    'Inside Bar Breakout':     strategy_inside_bar_breakout,
}"""

with open(WF_FILE, 'r') as f:
    content = f.read()

if OLD_FUNCS in content:
    content = content.replace(OLD_FUNCS, NEW_FUNCS)
    print("✓ Updated STRATEGY_FUNCS to 4 new + 2 legacy strategies")
else:
    print("⊘ STRATEGY_FUNCS already updated or pattern not found")

with open(WF_FILE, 'w') as f:
    f.write(content)

print("\nNext: python3 -c 'from scheduler import refresh_wf_scores; refresh_wf_scores()'")
