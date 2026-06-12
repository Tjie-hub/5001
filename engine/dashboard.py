"""Market dashboard aggregator — pure data layer for /api/dashboard/risk and /api/dashboard/watchlist."""

import sqlite3
from typing import Any


def get_risk_dashboard(db_path: str, date: str) -> dict[str, Any]:
    """Aggregate all market sensors into a single dashboard payload.

    Args:
        db_path: Path to walkforward.db.
        date:    ISO date string (YYYY-MM-DD) for which to compute the snapshot.

    Returns a dict with keys: date, risk_score, tier, components,
    ihsg, breadth, foreign_flow, vpin, accdist.
    """
    from engine.vpin import get_market_vpin_summary
    from engine.breadth import get_market_breadth
    from engine.technicals import detect_ihsg_technicals
    from engine.risk_score import compute_market_risk_score
    from flow_filter import get_market_accdist_summary

    conn = sqlite3.connect(db_path)
    try:
        vpin_s = _safe(get_market_vpin_summary, conn, date) or _empty_vpin()
        accdist_s = _safe_noconn(get_market_accdist_summary, date) or _empty_accdist(date)
        breadth_s = _safe(get_market_breadth, conn, date) or _empty_breadth(date)
        tech_s = _safe(detect_ihsg_technicals, conn, date) or _empty_tech(date)

        foreign_flow = _get_foreign_flow(conn, date)
        risk = compute_market_risk_score(
            vpin_s, accdist_s, breadth_s, tech_s, foreign_flow.get('net_5d')
        )

        ihsg = {
            'close': tech_s.get('close'),
            'ma5': tech_s.get('ma5'),
            'ma20': tech_s.get('ma20'),
            'death_cross': tech_s.get('death_cross', False),
            'lower_high': tech_s.get('lower_high', False),
            'support_breaks': tech_s.get('support_breaks', []),
            'ytd_pct': _calc_ytd(conn, date),
        }

        return {
            'date': date,
            'risk_score': risk['score'],
            'tier': risk['tier'],
            'components': risk.get('components', {}),
            'ihsg': ihsg,
            'breadth': breadth_s,
            'foreign_flow': foreign_flow,
            'vpin': vpin_s,
            'accdist': accdist_s,
        }
    finally:
        conn.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(fn, conn, date):
    try:
        return fn(conn, date)
    except Exception:
        return None


def _safe_noconn(fn, date):
    try:
        return fn(date)
    except Exception:
        return None


def _get_foreign_flow(conn: sqlite3.Connection, date: str) -> dict:
    """Compute Asing net flow: today, 5d, 20d from broker_flow table."""
    try:
        def _net(days: int) -> float:
            row = conn.execute(
                "SELECT "
                "  COALESCE(SUM(CASE WHEN side='BUY'  THEN lot_value ELSE 0 END), 0) "
                "- COALESCE(SUM(CASE WHEN side='SELL' THEN lot_value ELSE 0 END), 0) "
                "FROM broker_flow "
                "WHERE investor_type='Asing' "
                "  AND trade_date<=? AND trade_date>=date(?,?)",
                (date, date, f'-{days} days'),
            ).fetchone()
            return float(row[0]) if row else 0.0

        today_net = conn.execute(
            "SELECT "
            "  COALESCE(SUM(CASE WHEN side='BUY'  THEN lot_value ELSE 0 END), 0) "
            "- COALESCE(SUM(CASE WHEN side='SELL' THEN lot_value ELSE 0 END), 0) "
            "FROM broker_flow "
            "WHERE investor_type='Asing' AND trade_date=?",
            (date,),
        ).fetchone()
        today_val = float(today_net[0]) if today_net else 0.0
        net_5d = _net(5)
        net_20d = _net(20)
        trend = 'INFLOW' if net_5d > 0 else 'OUTFLOW' if net_5d < 0 else 'NEUTRAL'
        return {'today': today_val, 'net_5d': net_5d, 'net_20d': net_20d, 'trend': trend}
    except Exception:
        return {'today': None, 'net_5d': None, 'net_20d': None, 'trend': 'NEUTRAL'}


def _calc_ytd(conn: sqlite3.Connection, date: str) -> float | None:
    year = date[:4]
    start_row = conn.execute(
        "SELECT close FROM ohlcv WHERE ticker='IHSG' AND date>=? ORDER BY date LIMIT 1",
        (f'{year}-01-01',),
    ).fetchone()
    end_row = conn.execute(
        "SELECT close FROM ohlcv WHERE ticker='IHSG' AND date<=? ORDER BY date DESC LIMIT 1",
        (date,),
    ).fetchone()
    if start_row and end_row and start_row[0]:
        return round((end_row[0] - start_row[0]) / start_row[0] * 100, 2)
    return None


# ── Signals ───────────────────────────────────────────────────────────────────

def get_signals_dashboard(db_path: str, date: str) -> dict[str, Any]:
    """Aggregate agent decisions and today's scheduled signals for the dashboard.

    Returns:
        date, recent_decisions (last 20, newest first),
        signals_today (total, by_verdict, by_direction).
    """
    conn = sqlite3.connect(db_path)
    try:
        # Last 20 agent_decisions, newest first
        decisions = []
        for row in conn.execute(
            "SELECT id,scan_time,ticker,strategy,quant_score,decision,"
            "       confidence,size_hint,rationale "
            "FROM agent_decisions "
            "ORDER BY scan_time DESC, id DESC "
            "LIMIT 20"
        ):
            decisions.append({
                'id': row[0], 'scan_time': row[1], 'ticker': row[2],
                'strategy': row[3], 'quant_score': row[4], 'decision': row[5],
                'confidence': row[6], 'size_hint': row[7], 'rationale': row[8],
            })

        # Today's scheduled_signals grouped by verdict and direction
        by_verdict: dict[str, int] = {}
        by_direction: dict[str, int] = {}
        total = 0
        for row in conn.execute(
            "SELECT flow_verdict, signal_direction, COUNT(*) "
            "FROM scheduled_signals "
            "WHERE date(scan_time)=? AND signal_direction='BUY' "
            "GROUP BY flow_verdict, signal_direction",
            (date,),
        ):
            verdict, direction, count = row[0], row[1], row[2]
            total += count
            if verdict:
                by_verdict[verdict] = by_verdict.get(verdict, 0) + count
            if direction:
                by_direction[direction] = by_direction.get(direction, 0) + count

        return {
            'date': date,
            'recent_decisions': decisions,
            'signals_today': {
                'total': total,
                'by_verdict': by_verdict,
                'by_direction': by_direction,
            },
        }
    finally:
        conn.close()


# ── Watchlist ─────────────────────────────────────────────────────────────────

def get_watchlist(db_path: str, date: str) -> dict[str, Any]:
    """Compute BUY WATCH / AVOID / WAIT ticker lists for the dashboard.

    BUY WATCH: intraday bounce >3% + volume >50M + foreign net buy today >5B
    AVOID:     foreign net sell in 3d > 100B AND YTD drop >20%
    WAIT:      intraday bounce >3% + volume >50M + foreign net sell today
    """
    conn = sqlite3.connect(db_path)
    try:
        year = date[:4]
        jan_start = f'{year}-01-01'

        # Today's full OHLCV for all tickers (ex-IHSG)
        today_ohlcv: dict[str, dict] = {}
        for row in conn.execute(
            "SELECT ticker,open,high,low,close,volume "
            "FROM ohlcv WHERE date=? AND ticker!='IHSG'",
            (date,),
        ):
            today_ohlcv[row[0]] = {
                'open': row[1], 'high': row[2], 'low': row[3],
                'close': row[4], 'volume': row[5],
            }

        # Year-start closes — first trading date on or after Jan 1
        first_date = conn.execute(
            "SELECT MIN(date) FROM ohlcv WHERE date>=?", (jan_start,)
        ).fetchone()[0]
        jan_closes: dict[str, float] = {}
        if first_date:
            for row in conn.execute(
                "SELECT ticker,close FROM ohlcv WHERE date=? AND ticker!='IHSG'",
                (first_date,),
            ):
                jan_closes[row[0]] = float(row[1])

        # Foreign flow: today and last-3-days per ticker
        foreign_today: dict[str, float] = {}
        for row in conn.execute(
            "SELECT ticker,"
            "  SUM(CASE WHEN side='BUY' THEN lot_value ELSE 0 END)"
            "- SUM(CASE WHEN side='SELL' THEN lot_value ELSE 0 END) "
            "FROM broker_flow "
            "WHERE investor_type='Asing' AND trade_date=? "
            "GROUP BY ticker",
            (date,),
        ):
            foreign_today[row[0]] = float(row[1])

        foreign_3d: dict[str, float] = {}
        for row in conn.execute(
            "SELECT ticker,"
            "  SUM(CASE WHEN side='BUY' THEN lot_value ELSE 0 END)"
            "- SUM(CASE WHEN side='SELL' THEN lot_value ELSE 0 END) "
            "FROM broker_flow "
            "WHERE investor_type='Asing' "
            "  AND trade_date<=? AND trade_date>=date(?,'-3 days') "
            "GROUP BY ticker",
            (date, date),
        ):
            foreign_3d[row[0]] = float(row[1])

        def _ytd(ticker: str) -> float | None:
            c0 = jan_closes.get(ticker)
            c1 = today_ohlcv.get(ticker, {}).get('close')
            if c0 and c1 and c0 > 0:
                return round((c1 - c0) / c0 * 100, 2)
            return None

        def _build_entry(ticker: str, include_bounce: bool = False) -> dict:
            o = today_ohlcv.get(ticker, {})
            close = o.get('close')
            open_ = o.get('open')
            low   = o.get('low')
            chg   = round((close - open_) / open_ * 100, 2) if (close and open_) else None
            bounce = (
                round((close - low) / low * 100, 2)
                if (include_bounce and close and low and low > 0)
                else None
            )
            return {
                'ticker': ticker,
                'close': close,
                'chg_pct': chg,
                'bounce_pct': bounce,
                'foreign_net_today': foreign_today.get(ticker, 0.0),
                'foreign_net_3d': foreign_3d.get(ticker, 0.0),
                'volume': o.get('volume'),
                'ytd_pct': _ytd(ticker),
            }

        # Hammer tickers: bounce >3% AND volume >50M
        hammer: set[str] = set()
        for ticker, o in today_ohlcv.items():
            low = o['low']
            if low and low > 0 and o['volume'] and o['volume'] > 50_000_000:
                if (o['close'] - low) / low * 100 > 3:
                    hammer.add(ticker)

        buy_watch: list[dict] = []
        wait: list[dict] = []
        for ticker in hammer:
            net_today = foreign_today.get(ticker, 0.0)
            if net_today > 5_000_000_000:
                buy_watch.append(_build_entry(ticker, include_bounce=True))
            elif net_today < 0:
                wait.append(_build_entry(ticker, include_bounce=True))

        # AVOID: foreign net sell in 3d > 100B AND YTD drop > 20%
        avoid: list[dict] = []
        for ticker, net_3d in foreign_3d.items():
            ytd = _ytd(ticker)
            if net_3d < -100_000_000_000 and ytd is not None and ytd < -20:
                avoid.append(_build_entry(ticker))

        buy_watch.sort(key=lambda x: x['foreign_net_today'], reverse=True)
        avoid.sort(key=lambda x: x['foreign_net_3d'])
        wait.sort(key=lambda x: (x['bounce_pct'] or 0), reverse=True)

        return {'date': date, 'buy_watch': buy_watch, 'avoid': avoid, 'wait': wait}
    finally:
        conn.close()


# ── Checklist ─────────────────────────────────────────────────────────────────

def get_dashboard_checklist(db_path: str, date: str) -> dict[str, Any]:
    """Return today's operational checklist — which pipeline steps ran.

    Returns:
        date, items (list of {name, done, count, detail}),
        last_scan, all_done (OHLCV + signals both present).
    """
    conn = sqlite3.connect(db_path)
    try:
        def _count(sql: str, *params) -> int:
            try:
                return conn.execute(sql, params).fetchone()[0] or 0
            except Exception:
                return 0

        ohlcv_count   = _count("SELECT COUNT(DISTINCT ticker) FROM ohlcv WHERE date=?", date)
        flow_count    = _count("SELECT COUNT(*) FROM broker_flow WHERE trade_date=?", date)
        signals_count = _count("SELECT COUNT(*) FROM scheduled_signals WHERE date(scan_time)=?", date)
        agent_count   = _count("SELECT COUNT(*) FROM agent_decisions WHERE date(scan_time)=?", date)

        try:
            last_scan = conn.execute(
                "SELECT MAX(scan_time) FROM scheduled_signals"
            ).fetchone()[0]
        except Exception:
            last_scan = None

        items = [
            {'name': 'OHLCV data',      'done': ohlcv_count > 0,   'count': ohlcv_count,   'detail': f'{ohlcv_count} tickers'},
            {'name': 'Broker flow',     'done': flow_count > 0,    'count': flow_count,    'detail': f'{flow_count} records'},
            {'name': 'Signals scanned', 'done': signals_count > 0, 'count': signals_count, 'detail': f'{signals_count} signals'},
            {'name': 'Agent reviews',   'done': agent_count > 0,   'count': agent_count,   'detail': f'{agent_count} decisions'},
        ]
        return {
            'date': date,
            'items': items,
            'last_scan': last_scan,
            'all_done': ohlcv_count > 0 and signals_count > 0,
        }
    finally:
        conn.close()


# ── Empty fallbacks ───────────────────────────────────────────────────────────

def _empty_vpin():
    return {'avg_vpin': 0.0, 'pct_above_08': 0.0, 'pct_above_095': 0.0,
            'label': 'INSUFFICIENT_DATA'}


def _empty_accdist(date):
    return {'date': date, 'total': 0, 'dist_count': 0, 'acc_count': 0,
            'neutral_count': 0, 'dist_pct': 0.0, 'acc_pct': 0.0,
            'avg_numeric_score': 0.0, 'label': 'NEUTRAL'}


def _empty_breadth(date):
    return {'date': date, 'advancers': 0, 'decliners': 0, 'unchanged': 0,
            'adv_dec_ratio': 0.0, 'pct_advancing': 0.0, 'pct_above_ma20': 0.0,
            'label': 'INSUFFICIENT_DATA'}


def _empty_tech(date):
    return {'date': date, 'close': None, 'ma5': None, 'ma20': None,
            'death_cross': False, 'lower_high': False, 'support_breaks': [],
            'label': 'INSUFFICIENT_DATA'}
