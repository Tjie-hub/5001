"""Tests for engine.technicals.tech_direction — deterministic MA-structure call."""
from engine.technicals import tech_direction


class TestTechDirection:
    def test_insufficient_data_is_neutral(self):
        assert tech_direction([1, 2, 3]) == 'NEUTRAL'
        assert tech_direction([]) == 'NEUTRAL'

    def test_uptrend_is_bullish(self):
        # steadily rising → last close above MA, short MA above long MA
        closes = [100 + i for i in range(60)]
        assert tech_direction(closes) == 'BULLISH'

    def test_downtrend_is_bearish(self):
        closes = [200 - i for i in range(60)]
        assert tech_direction(closes) == 'BEARISH'

    def test_flat_is_neutral(self):
        closes = [100.0] * 60   # close == MAs → neither cleanly bull nor bear
        assert tech_direction(closes) == 'NEUTRAL'

    def test_short_window_falls_back_without_long_ma(self):
        # exactly `short`+1 rising bars, fewer than `long` → still classifiable
        closes = [100 + i for i in range(21)]
        assert tech_direction(closes, short=20, long=50) == 'BULLISH'
