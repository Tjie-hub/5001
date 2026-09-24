"""RC-0001-MAX rule script: the signal is what the card says, and the card is a valid draft.

The card must stay a DRAFT until the Owner rules on the PENDING fields — strict
validation (the freeze gate) must refuse it while any PENDING remains.
"""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from research.rulecard import card as cardmod
from research.rulecard import checks, engine, synthetic

CARD_DIR = Path(__file__).resolve().parents[1] / "docs" / "research_programs" / "P-M" / "rulecards" / "RC-0001-MAX"


def _rule():
    spec = importlib.util.spec_from_file_location("rc0001_rule", CARD_DIR / "rule.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_signal_is_the_max_daily_return_of_the_calendar_month():
    raw = synthetic.make_panel(n_tickers=5, years=1, seed=31)
    P = engine.prepare(raw)
    s = _rule().signal(P)
    r = P.groupby("ticker")["close"].pct_change()
    for tk in ("S000", "S003"):
        m = (P.ticker == tk) & (P.date.dt.to_period("M") == pd.Period("2015-03", "M"))
        assert s[m].iloc[-1] == pytest.approx(r[m].max())
        assert np.all(np.diff(s[m].values) >= 0)              # running max within the month


def test_signal_uses_no_future_rows():
    pan = engine.Panel(synthetic.make_panel(n_tickers=60, years=3, seed=32))
    rule = _rule()
    forms = list(engine.calendar(pan.P)["formation"])
    assert checks.prefix_invariance(pan, rule.signal, rule.signal(pan.P), forms)["status"] == "PASS"


def test_card_is_closed_underpowered_and_can_never_be_frozen():
    card = cardmod.load(CARD_DIR / "CARD.yaml")
    assert card["disposition"]["status"] == "NOT_TESTED_UNDERPOWERED"
    table = cardmod.validate(card, strict=False)            # still a readable, valid record
    assert not table["admissible"]                          # 0.80 < needed with the noise floor
    with pytest.raises(cardmod.CardError) as e:
        cardmod.validate(card, strict=True)
    assert any("card is closed" in p for p in e.value.problems)
