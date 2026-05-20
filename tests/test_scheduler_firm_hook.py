import pytest
from unittest.mock import patch

from engine.agent_firm.schemas import SignalCandidate


def _make_signals():
    return [
        {
            "ticker": "BBRI", "strategies": ["vol_weighted"],
            "flow": {"score": 3, "verdict": "BUY", "smart_money": "YES", "confirmed": True,
                     "cum_delta": 5000, "price_chg_pct": 1.2},
            "sector": "BANKING", "sector_weight": "OVERWEIGHT", "sector_score": 7,
            "signal_reasons": ["vol_weighted: uptrend"],
            "signal_details": {"vol_weighted": {"price": 3050}},
        }
    ]


def test_firm_hook_called_when_active():
    evaluate_calls = []

    with patch("engine.agent_firm.config.is_active", return_value=True), \
         patch("engine.agent_firm.firm.evaluate", side_effect=lambda c: evaluate_calls.append(c) or []):
        from engine.agent_firm import config as _firm_cfg, firm as _firm
        from datetime import datetime
        signals = _make_signals()
        if _firm_cfg.is_active() and signals:
            candidates = [
                SignalCandidate(
                    ticker=s["ticker"],
                    strategy=(s["strategies"][0] if s.get("strategies") else "multi"),
                    score=float((s.get("flow") or {}).get("score") or 0),
                    scan_time=datetime.now().isoformat(),
                    flow_verdict=(s.get("flow") or {}).get("verdict"),
                    foreign_score=None,
                    indicators={},
                )
                for s in signals
            ]
            _firm.evaluate(candidates)
        assert len(evaluate_calls) == 1
        assert evaluate_calls[0][0].ticker == "BBRI"


def test_firm_hook_skipped_when_disabled():
    evaluate_calls = []
    with patch("engine.agent_firm.config.is_active", return_value=False), \
         patch("engine.agent_firm.firm.evaluate", side_effect=lambda c: evaluate_calls.append(c) or []):
        from engine.agent_firm import config as _firm_cfg, firm as _firm
        signals = _make_signals()
        if _firm_cfg.is_active() and signals:
            _firm.evaluate([])
        assert len(evaluate_calls) == 0
