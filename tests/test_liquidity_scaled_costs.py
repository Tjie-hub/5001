"""Liquidity-scaled slippage (audit P4-6) — opt-in ADV bucketing, never the
default apply_costs()/Costs()/SLIPPAGE path."""
import pytest

from engine.exits.costs import (
    COMMISSION_BUY, COMMISSION_SELL, SLIPPAGE,
    liquidity_scaled_costs, liquidity_scaled_slippage,
)


def test_top_bucket_matches_flat_default():
    """The most-liquid bucket must reproduce the existing flat rate exactly --
    no silent behavior change for names that were already well-liquid."""
    assert liquidity_scaled_slippage(50_000_000_000) == SLIPPAGE


def test_slippage_increases_as_adv_falls():
    high = liquidity_scaled_slippage(30_000_000_000)
    mid = liquidity_scaled_slippage(15_000_000_000)
    low = liquidity_scaled_slippage(6_000_000_000)
    assert high < mid < low


def test_none_or_negative_adv_is_treated_as_worst_bucket():
    worst = liquidity_scaled_slippage(0)
    assert liquidity_scaled_slippage(None) == worst
    assert liquidity_scaled_slippage(-1) == worst


def test_liquidity_scaled_costs_keeps_commissions_unchanged():
    c = liquidity_scaled_costs(6_000_000_000)
    assert c.commission_buy == COMMISSION_BUY
    assert c.commission_sell == COMMISSION_SELL
    assert c.slippage == liquidity_scaled_slippage(6_000_000_000)
    assert c.slippage != SLIPPAGE
