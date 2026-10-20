"""data.fetcher index lists (updated 2026-10-20 to the 3 Aug - 30 Oct 2026 period): sizes, no repeats, nesting.

The lists had silently aged past several reconstitutions (11 of 30 IDX30 names had left). This does not pin the
members -- they change every quarter -- only the shape a correct update must keep."""
from data.fetcher import IDX30, IDX80, LQ45


def test_sizes_and_no_repeats():
    assert (len(IDX30), len(LQ45), len(IDX80)) == (30, 45, 80)
    assert len(set(IDX80)) == 80


def test_indices_nest():
    assert set(IDX30) <= set(LQ45) <= set(IDX80)
