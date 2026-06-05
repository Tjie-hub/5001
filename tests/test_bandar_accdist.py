"""Tests for C2 — bandar_detector accdist numeric pipeline.

Root cause: broker_accdist stores text labels ('Acc', 'Dist') but no code
converts them to numbers. Queries that CAST text to REAL get 0.0 for every
row, creating 100% accumulation bias. This module tests the conversion layer
and market-wide summary function.
"""
import sqlite3
import tempfile
import os
from unittest.mock import patch

from flow_filter import accdist_label_to_score, get_market_accdist_summary


# ── accdist_label_to_score ────────────────────────────────────────────────────

def test_big_acc_maps_to_plus_3():
    assert accdist_label_to_score('Big Acc') == 3

def test_normal_acc_maps_to_plus_2():
    assert accdist_label_to_score('Normal Acc') == 2

def test_small_acc_maps_to_plus_1():
    assert accdist_label_to_score('Small Acc') == 1

def test_neutral_maps_to_zero():
    assert accdist_label_to_score('Neutral') == 0

def test_small_dist_maps_to_minus_1():
    assert accdist_label_to_score('Small Dist') == -1

def test_normal_dist_maps_to_minus_2():
    assert accdist_label_to_score('Normal Dist') == -2

def test_big_dist_maps_to_minus_3():
    assert accdist_label_to_score('Big Dist') == -3

def test_acc_shorthand_maps_to_plus_1():
    """Top-level broker_accdist stores short 'Acc' label."""
    assert accdist_label_to_score('Acc') == 1

def test_dist_shorthand_maps_to_minus_1():
    """Top-level broker_accdist stores short 'Dist' label."""
    assert accdist_label_to_score('Dist') == -1

def test_none_maps_to_zero():
    assert accdist_label_to_score(None) == 0

def test_unknown_label_maps_to_zero():
    assert accdist_label_to_score('SOMETHING_WEIRD') == 0

def test_empty_string_maps_to_zero():
    assert accdist_label_to_score('') == 0


# ── get_market_accdist_summary ────────────────────────────────────────────────

def _make_bandar_db(rows):
    """Create temp SQLite DB with bandar_detector rows. Returns path."""
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute("""
        CREATE TABLE bandar_detector (
            ticker TEXT, trade_date TEXT, broker_accdist TEXT,
            avg_accdist TEXT, top5_accdist TEXT,
            PRIMARY KEY (ticker, trade_date)
        )
    """)
    conn.executemany(
        "INSERT INTO bandar_detector (ticker, trade_date, broker_accdist, avg_accdist, top5_accdist) VALUES (?,?,?,?,?)",
        rows
    )
    conn.commit()
    conn.close()
    return tmp.name


def test_summary_counts_dist_and_acc_correctly():
    """Heavy distribution day: dist_count and acc_count are correct."""
    db = _make_bandar_db([
        ('BRPT', '2026-05-08', 'Dist', 'Big Dist', 'Normal Dist'),
        ('TLKM', '2026-05-08', 'Dist', 'Normal Dist', 'Small Dist'),
        ('BBCA', '2026-05-08', 'Acc',  'Small Acc',  'Neutral'),
        ('BMRI', '2026-05-08', 'Dist', 'Normal Dist', 'Normal Dist'),
    ])
    with patch('flow_filter._DB_PATH', db):
        result = get_market_accdist_summary('2026-05-08')
    os.unlink(db)

    assert result['total'] == 4
    assert result['dist_count'] == 3
    assert result['acc_count'] == 1


def test_summary_dist_pct_computed_correctly():
    """dist_pct = dist_count / total * 100."""
    db = _make_bandar_db([
        ('A', '2026-06-02', 'Dist', 'Neutral', 'Neutral'),
        ('B', '2026-06-02', 'Dist', 'Neutral', 'Neutral'),
        ('C', '2026-06-02', 'Dist', 'Neutral', 'Neutral'),
        ('D', '2026-06-02', 'Acc',  'Neutral', 'Neutral'),
    ])
    with patch('flow_filter._DB_PATH', db):
        result = get_market_accdist_summary('2026-06-02')
    os.unlink(db)

    assert result['dist_pct'] == 75.0
    assert result['acc_pct'] == 25.0


def test_summary_avg_numeric_score_is_negative_on_distribution_day():
    """avg_numeric_score is negative when distribution dominates."""
    db = _make_bandar_db([
        ('A', '2026-05-08', 'Dist', 'Big Dist', 'Normal Dist'),
        ('B', '2026-05-08', 'Dist', 'Normal Dist', 'Small Dist'),
        ('C', '2026-05-08', 'Dist', 'Normal Dist', 'Normal Dist'),
        ('D', '2026-05-08', 'Acc',  'Small Acc',  'Neutral'),
    ])
    with patch('flow_filter._DB_PATH', db):
        result = get_market_accdist_summary('2026-05-08')
    os.unlink(db)

    assert result['avg_numeric_score'] < 0, \
        f"avg_numeric_score should be negative, got {result['avg_numeric_score']}"


def test_summary_label_is_distribution_when_dist_dominates():
    """70%+ distribution → label = 'DISTRIBUTION'."""
    db = _make_bandar_db([
        ('A', '2026-05-08', 'Dist', 'Big Dist', 'Big Dist'),
        ('B', '2026-05-08', 'Dist', 'Big Dist', 'Big Dist'),
        ('C', '2026-05-08', 'Dist', 'Big Dist', 'Big Dist'),
        ('D', '2026-05-08', 'Acc',  'Neutral',  'Neutral'),
    ])
    with patch('flow_filter._DB_PATH', db):
        result = get_market_accdist_summary('2026-05-08')
    os.unlink(db)

    assert result['label'] in ('DISTRIBUTION', 'STRONG_DISTRIBUTION')


def test_summary_label_is_neutral_on_balanced_day():
    """50/50 split → label = 'NEUTRAL'."""
    db = _make_bandar_db([
        ('A', '2026-06-01', 'Dist', 'Neutral', 'Neutral'),
        ('B', '2026-06-01', 'Dist', 'Neutral', 'Neutral'),
        ('C', '2026-06-01', 'Acc',  'Neutral', 'Neutral'),
        ('D', '2026-06-01', 'Acc',  'Neutral', 'Neutral'),
    ])
    with patch('flow_filter._DB_PATH', db):
        result = get_market_accdist_summary('2026-06-01')
    os.unlink(db)

    assert result['label'] == 'NEUTRAL'


def test_summary_returns_empty_when_no_data():
    """No bandar_detector rows for date → returns empty/zero summary."""
    db = _make_bandar_db([])
    with patch('flow_filter._DB_PATH', db):
        result = get_market_accdist_summary('2099-01-01')
    os.unlink(db)

    assert result['total'] == 0
    assert result['avg_numeric_score'] == 0.0
    assert result['label'] == 'NEUTRAL'


def test_summary_uses_today_as_default_date():
    """get_market_accdist_summary() with no args uses today's date."""
    import datetime
    today = str(datetime.date.today())
    db = _make_bandar_db([
        ('BBRI', today, 'Acc', 'Small Acc', 'Neutral'),
    ])
    with patch('flow_filter._DB_PATH', db):
        result = get_market_accdist_summary()
    os.unlink(db)

    assert result['date'] == today
    assert result['total'] == 1
