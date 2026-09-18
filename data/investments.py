"""Canonical investment portfolio store (consolidation 2026-09-03).

Absorbs the Investment Dashboard's (port 5003) personal ledger — equity
transactions, closed equity trades, mutual fund positions, dividends and
manual prices — into the single walkforward.db, so there is exactly one
portfolio data model in the Production OS. The 5003 single-file app kept this
state in localStorage + Google Sheets; that sync is superseded by this store
(the last Sheets snapshot is archived under backups/migration_5003_20260903/).

Fee model mirrors 5003 exactly (BUY_FEE factored into average cost, SELL_FEE
into breakeven/net-if-sold, flat default dividend tax) so the numbers an
operator saw on 5003 reproduce here to the rupiah.

All table creation is additive and idempotent; nothing outside inv_* is
touched. Every function takes db_path=None meaning config.DB_PATH, so tests
can point the whole store at a tmp file.
"""
import logging
import sqlite3
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from data.db import connect as db_connect

log = logging.getLogger("investments")

BUY_FEE = 0.0015    # 0.15% — included in average cost, as on 5003
SELL_FEE = 0.0025   # 0.25% — breakeven = avg_cost / (1 - SELL_FEE)
DEFAULT_DIV_TAX_PCT = 10.0  # IDX PPh Final default on 5003

# Server-side price fetching allowlist (replaces 5003's public CORS proxy).
YAHOO_URL = "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_ALLOWED_HOSTS = {"query1.finance.yahoo.com", "query2.finance.yahoo.com"}
YAHOO_SUFFIX = ".JK"
_PRICE_FETCH_TIMEOUT_S = 10
_PRICE_FETCH_GAP_S = 0.4


def _db(db_path=None):
    return db_connect(db_path)


def init_investment_tables(db_path=None):
    """Idempotent migration for the canonical investment tables."""
    conn = _db(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS inv_transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            ticker      TEXT NOT NULL,
            type        TEXT NOT NULL CHECK (type IN ('BUY','SELL')),
            price       REAL NOT NULL,
            qty         REAL NOT NULL,
            notes       TEXT DEFAULT '',
            external_id TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_inv_txns_ticker ON inv_transactions(ticker);
        CREATE UNIQUE INDEX IF NOT EXISTS ux_inv_txns_external
            ON inv_transactions(external_id) WHERE external_id IS NOT NULL;

        CREATE TABLE IF NOT EXISTS inv_closed_equity (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date  TEXT NOT NULL,
            exit_date   TEXT NOT NULL,
            ticker      TEXT NOT NULL,
            entry_price REAL NOT NULL,
            exit_price  REAL NOT NULL,
            qty         REAL NOT NULL,
            net_pl      REAL NOT NULL,
            pl_pct      REAL NOT NULL,
            notes       TEXT DEFAULT '',
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(entry_date, exit_date, ticker, exit_price, qty)
        );

        CREATE TABLE IF NOT EXISTS inv_fund_positions (
            id           TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','CLOSED')),
            entry_date   TEXT NOT NULL,
            exit_date    TEXT,
            entry_nav    REAL NOT NULL,
            exit_nav     REAL,
            units        REAL NOT NULL,
            cost_basis   REAL NOT NULL,
            current_nav  REAL,
            total_return REAL,
            net_pl       REAL,
            pl_pct       REAL,
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS inv_dividends (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            ticker      TEXT NOT NULL,
            per_share   REAL NOT NULL,
            qty         REAL NOT NULL,
            tax_pct     REAL NOT NULL DEFAULT 10.0,
            notes       TEXT DEFAULT '',
            external_id TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_inv_div_external
            ON inv_dividends(external_id) WHERE external_id IS NOT NULL;

        CREATE TABLE IF NOT EXISTS inv_prices (
            ticker     TEXT PRIMARY KEY,
            price      REAL NOT NULL,
            source     TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual','yahoo')),
            updated_at TEXT
        );
    """)
    conn.commit()

    # Additive column migration for stores created before current_nav existed
    # (CREATE TABLE IF NOT EXISTS won't alter a table that's already there).
    existing = {r[1] for r in conn.execute("PRAGMA table_info(inv_fund_positions)")}
    if "current_nav" not in existing:
        conn.execute("ALTER TABLE inv_fund_positions ADD COLUMN current_nav REAL")
        conn.commit()

    conn.close()


def _norm_date(value):
    """5003 stored <input type=date> picks as UTC ISO instants
    (e.g. '2020-12-31T17:00:00.000Z' = 2021-01-01 WIB); recover the WIB
    calendar date. Plain YYYY-MM-DD strings pass through."""
    if isinstance(value, str):
        s = value.strip()
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            head = s[:10]
            if "T" in s or "Z" in s or "+" in s[10:]:
                try:
                    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return (dt + timedelta(hours=7)).date().isoformat()
                except ValueError:
                    return head
            return head
        return s
    return str(value)


# ---------------------------------------------------------------------------
# prices
# ---------------------------------------------------------------------------

def set_price(ticker, price, source="manual", db_path=None):
    conn = _db(db_path)
    conn.execute(
        "INSERT INTO inv_prices (ticker, price, source, updated_at) VALUES (?,?,?,?) "
        "ON CONFLICT(ticker) DO UPDATE SET price=excluded.price, source=excluded.source, "
        "updated_at=excluded.updated_at",
        (ticker, float(price), source, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def get_prices(db_path=None):
    conn = _db(db_path)
    rows = conn.execute("SELECT ticker, price, source, updated_at FROM inv_prices").fetchall()
    conn.close()
    return {r[0]: {"price": r[1], "source": r[2], "updated_at": r[3]} for r in rows}


def _fetch_yahoo_price(ticker):
    """One Yahoo chart quote for <ticker>.JK. Returns (price, None) or
    (None, reason). Host-validated against the allowlist before requesting."""
    symbol = f"{ticker}{YAHOO_SUFFIX}"
    url = YAHOO_URL.format(symbol=urllib.parse.quote(symbol))
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in YAHOO_ALLOWED_HOSTS:
        return None, f"blocked non-allowlisted url host {parsed.hostname!r}"
    req = urllib.request.Request(url, headers={"User-Agent": "idx-walkforward/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=_PRICE_FETCH_TIMEOUT_S) as resp:
            import json as _json
            payload = _json.loads(resp.read().decode("utf-8", "replace"))
        result = (payload.get("chart") or {}).get("result") or []
        price = ((result[0] or {}).get("meta") or {}).get("regularMarketPrice")
        if price is None:
            return None, "no regularMarketPrice in response"
        return float(price), None
    except Exception as e:  # network/HTTP/parse — reported per ticker, never fatal
        return None, str(e)


def refresh_prices(db_path=None, tickers=None):
    """Refresh prices from Yahoo for the given tickers (default: open equity
    holdings). Returns per-ticker {'price'} or {'error'} rows; a failed
    ticker never blocks the others and never fails the whole call."""
    if tickers is None:
        holdings = compute_holdings(db_path)
        tickers = [h["ticker"] for h in holdings["holdings"]]
    results = {}
    for i, ticker in enumerate(sorted({t.upper() for t in tickers})):
        if i:
            time.sleep(_PRICE_FETCH_GAP_S)
        price, err = _fetch_yahoo_price(ticker)
        if err is None:
            set_price(ticker, price, source="yahoo", db_path=db_path)
            results[ticker] = {"price": price}
        else:
            log.warning("price refresh failed for %s: %s", ticker, err)
            results[ticker] = {"error": err}
    return results


# ---------------------------------------------------------------------------
# transactions / holdings
# ---------------------------------------------------------------------------

def list_transactions(db_path=None):
    conn = _db(db_path)
    rows = conn.execute(
        "SELECT id, date, ticker, type, price, qty, notes FROM inv_transactions "
        "ORDER BY date, id"
    ).fetchall()
    conn.close()
    return [
        {"id": r[0], "date": r[1], "ticker": r[2], "type": r[3],
         "price": r[4], "qty": r[5], "notes": r[6]}
        for r in rows
    ]


def add_transaction(date, ticker, txn_type, price, qty, notes="", db_path=None,
                    external_id=None):
    ticker = str(ticker).strip().upper()
    txn_type = str(txn_type).strip().upper()
    price = float(price)
    qty = float(qty)
    if not ticker:
        raise ValueError("ticker is required")
    if txn_type not in ("BUY", "SELL"):
        raise ValueError("type must be BUY or SELL")
    if price <= 0:
        raise ValueError("price must be > 0")
    if qty <= 0:
        raise ValueError("qty must be > 0")
    date = _norm_date(date)
    conn = _db(db_path)
    cur = conn.execute(
        "INSERT OR IGNORE INTO inv_transactions (date, ticker, type, price, qty, notes, external_id) "
        "VALUES (?,?,?,?,?,?,?)",
        (date, ticker, txn_type, price, qty, notes or "",
         str(external_id) if external_id is not None else None),
    )
    conn.commit()
    txn_id = cur.lastrowid if cur.rowcount else None
    conn.close()
    return txn_id


def delete_transaction(txn_id, db_path=None):
    conn = _db(db_path)
    cur = conn.execute("DELETE FROM inv_transactions WHERE id=?", (int(txn_id),))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return deleted


def compute_holdings(db_path=None):
    """Open equity holdings from the transaction ledger, using 5003's
    average-cost method: BUY adds qty and fee-loaded cost; SELL reduces qty
    and cost at the running average price. Rows carry the per-position
    analytics the 5003 Equities tab showed."""
    conn = _db(db_path)
    txns = conn.execute(
        "SELECT ticker, type, price, qty FROM inv_transactions ORDER BY date, id"
    ).fetchall()
    tranche_counts = {}
    for t in txns:
        tranche_counts[t[0]] = tranche_counts.get(t[0], 0) + 1

    state = {}  # ticker -> [qty, net_cost]
    for ticker, txn_type, price, qty in txns:
        slot = state.setdefault(ticker, [0.0, 0.0])
        if txn_type == "BUY":
            slot[0] += qty
            slot[1] += qty * price * (1 + BUY_FEE)
        else:  # SELL
            avg = (slot[1] / slot[0]) if slot[0] > 0 else price
            slot[0] -= qty
            slot[1] -= qty * avg

    prices = get_prices(db_path)
    holdings = []
    for ticker, (qty, net_cost) in state.items():
        if qty <= 1e-9:
            continue
        avg_price = net_cost / qty
        live = prices.get(ticker, {}).get("price") or 0.0
        market_value = qty * live
        breakeven = avg_price / (1 - SELL_FEE)
        net_if_sold = market_value * (1 - SELL_FEE)
        unrealized = market_value - net_cost
        holdings.append({
            "ticker": ticker,
            "qty": qty,
            "avg_price": avg_price,
            "breakeven": breakeven,
            "price": live,
            "price_source": prices.get(ticker, {}).get("source"),
            "price_updated_at": prices.get(ticker, {}).get("updated_at"),
            "market_value": market_value,
            "cost_basis": net_cost,
            "unrealized_pl": unrealized,
            "unrealized_pct": (unrealized / net_cost * 100) if net_cost else 0.0,
            "net_if_sold": net_if_sold,
            "net_pl": net_if_sold - net_cost,
            "net_pct": ((net_if_sold - net_cost) / net_cost * 100) if net_cost else 0.0,
            "tranches": tranche_counts.get(ticker, 0),
        })
    holdings.sort(key=lambda h: -h["market_value"])
    conn.close()
    totals = {
        "market_value": sum(h["market_value"] for h in holdings),
        "cost_basis": sum(h["cost_basis"] for h in holdings),
        "unrealized_pl": sum(h["unrealized_pl"] for h in holdings),
        "net_if_sold": sum(h["net_if_sold"] for h in holdings),
    }
    totals["unrealized_pct"] = (
        totals["unrealized_pl"] / totals["cost_basis"] * 100 if totals["cost_basis"] else 0.0
    )
    return {"holdings": holdings, "totals": totals}


# ---------------------------------------------------------------------------
# closed equity journal
# ---------------------------------------------------------------------------

def list_closed_equity(db_path=None):
    conn = _db(db_path)
    rows = conn.execute(
        "SELECT id, entry_date, exit_date, ticker, entry_price, exit_price, qty, net_pl, pl_pct "
        "FROM inv_closed_equity ORDER BY exit_date, id"
    ).fetchall()
    conn.close()
    return [
        {"id": r[0], "entry_date": r[1], "exit_date": r[2], "ticker": r[3],
         "entry_price": r[4], "exit_price": r[5], "qty": r[6], "net_pl": r[7], "pl_pct": r[8]}
        for r in rows
    ]


def add_closed_equity(entry_date, exit_date, ticker, entry_price, exit_price, qty,
                      net_pl, pl_pct, db_path=None):
    conn = _db(db_path)
    cur = conn.execute(
        "INSERT OR IGNORE INTO inv_closed_equity "
        "(entry_date, exit_date, ticker, entry_price, exit_price, qty, net_pl, pl_pct) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (_norm_date(entry_date), _norm_date(exit_date), str(ticker).strip().upper(),
         float(entry_price), float(exit_price), float(qty), float(net_pl), float(pl_pct)),
    )
    conn.commit()
    added = cur.rowcount
    conn.close()
    return added


def delete_closed_equity(row_id, db_path=None):
    conn = _db(db_path)
    cur = conn.execute("DELETE FROM inv_closed_equity WHERE id=?", (int(row_id),))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return deleted


# ---------------------------------------------------------------------------
# mutual funds
# ---------------------------------------------------------------------------

def list_funds(status="ALL", db_path=None):
    conn = _db(db_path)
    if status in ("OPEN", "CLOSED"):
        rows = conn.execute(
            "SELECT id, name, status, entry_date, exit_date, entry_nav, exit_nav, units, "
            "cost_basis, current_nav, total_return, net_pl, pl_pct FROM inv_fund_positions "
            "WHERE status=? ORDER BY entry_date, id", (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, name, status, entry_date, exit_date, entry_nav, exit_nav, units, "
            "cost_basis, current_nav, total_return, net_pl, pl_pct FROM inv_fund_positions "
            "ORDER BY status, entry_date, id"
        ).fetchall()
    conn.close()
    return [
        {"id": r[0], "name": r[1], "status": r[2], "entry_date": r[3], "exit_date": r[4],
         "entry_nav": r[5], "exit_nav": r[6], "units": r[7], "cost_basis": r[8],
         "current_nav": r[9], "total_return": r[10], "net_pl": r[11], "pl_pct": r[12]}
        for r in rows
    ]


def add_fund(fund_id, name, entry_date, entry_nav, cost_basis, db_path=None):
    """Units derive from cost/nav exactly as 5003's add form did."""
    entry_nav = float(entry_nav)
    cost_basis = float(cost_basis)
    if entry_nav <= 0:
        raise ValueError("entry_nav must be > 0")
    if cost_basis <= 0:
        raise ValueError("cost_basis must be > 0")
    conn = _db(db_path)
    conn.execute(
        "INSERT INTO inv_fund_positions (id, name, status, entry_date, entry_nav, units, cost_basis) "
        "VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, "
        "status='OPEN', entry_date=excluded.entry_date, entry_nav=excluded.entry_nav, "
        "units=excluded.units, cost_basis=excluded.cost_basis, exit_date=NULL, exit_nav=NULL, "
        "total_return=NULL, net_pl=NULL, pl_pct=NULL",
        (str(fund_id), str(name), "OPEN", _norm_date(entry_date), entry_nav,
         cost_basis / entry_nav, cost_basis),
    )
    conn.commit()
    conn.close()


def redeem_fund(fund_id, exit_date, exit_nav, db_path=None):
    """Close an OPEN position: compute total return / net P&L as 5003's
    redeem modal did, flip status to CLOSED."""
    exit_nav = float(exit_nav)
    if exit_nav <= 0:
        raise ValueError("exit_nav must be > 0")
    conn = _db(db_path)
    row = conn.execute(
        "SELECT status, units, cost_basis FROM inv_fund_positions WHERE id=?", (str(fund_id),)
    ).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"unknown fund position: {fund_id}")
    if row[0] != "OPEN":
        conn.close()
        raise ValueError(f"fund position {fund_id} is not OPEN")
    units, cost_basis = row[1], row[2]
    total_return = units * exit_nav
    net_pl = total_return - cost_basis
    pl_pct = (net_pl / cost_basis * 100) if cost_basis else 0.0
    conn.execute(
        "UPDATE inv_fund_positions SET status='CLOSED', exit_date=?, exit_nav=?, "
        "total_return=?, net_pl=?, pl_pct=? WHERE id=?",
        (_norm_date(exit_date), exit_nav, total_return, net_pl, pl_pct, str(fund_id)),
    )
    conn.commit()
    conn.close()
    return {"total_return": total_return, "net_pl": net_pl, "pl_pct": pl_pct}


def set_fund_nav(fund_id, current_nav, db_path=None):
    """Manual NAV update for an OPEN position (5003's 'Manual' toolbar flow).
    Valuation uses current_nav when present, entry_nav otherwise."""
    current_nav = float(current_nav)
    if current_nav <= 0:
        raise ValueError("current_nav must be > 0")
    conn = _db(db_path)
    cur = conn.execute(
        "UPDATE inv_fund_positions SET current_nav=? WHERE id=? AND status='OPEN'",
        (current_nav, str(fund_id)),
    )
    conn.commit()
    updated = cur.rowcount
    conn.close()
    if not updated:
        raise ValueError(f"no OPEN fund position: {fund_id}")


def delete_fund(fund_id, db_path=None):
    conn = _db(db_path)
    cur = conn.execute("DELETE FROM inv_fund_positions WHERE id=?", (str(fund_id),))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return deleted


# ---------------------------------------------------------------------------
# dividends
# ---------------------------------------------------------------------------

def dividend_net(per_share, qty, tax_pct):
    gross = per_share * qty
    tax = gross * tax_pct / 100.0
    return {"gross": gross, "tax": tax, "net": gross - tax}


def list_dividends(db_path=None):
    conn = _db(db_path)
    rows = conn.execute(
        "SELECT id, date, ticker, per_share, qty, tax_pct, notes FROM inv_dividends "
        "ORDER BY date DESC, id DESC"
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        entry = {"id": r[0], "date": r[1], "ticker": r[2], "per_share": r[3],
                 "qty": r[4], "tax_pct": r[5], "notes": r[6]}
        entry.update(dividend_net(r[3], r[4], r[5]))
        out.append(entry)
    return out


def add_dividend(date, ticker, per_share, qty, tax_pct=DEFAULT_DIV_TAX_PCT, notes="",
                 db_path=None, external_id=None):
    per_share = float(per_share)
    qty = float(qty)
    tax_pct = float(tax_pct)
    if per_share <= 0:
        raise ValueError("per_share must be > 0")
    if qty <= 0:
        raise ValueError("qty must be > 0")
    if not 0 <= tax_pct <= 100:
        raise ValueError("tax_pct must be within 0..100")
    conn = _db(db_path)
    cur = conn.execute(
        "INSERT OR IGNORE INTO inv_dividends (date, ticker, per_share, qty, tax_pct, notes, external_id) "
        "VALUES (?,?,?,?,?,?,?)",
        (_norm_date(date), str(ticker).strip().upper(), per_share, qty, tax_pct, notes or "",
         str(external_id) if external_id is not None else None),
    )
    conn.commit()
    added = cur.rowcount
    conn.close()
    return added


def delete_dividend(row_id, db_path=None):
    conn = _db(db_path)
    cur = conn.execute("DELETE FROM inv_dividends WHERE id=?", (int(row_id),))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return deleted


# ---------------------------------------------------------------------------
# overview summary
# ---------------------------------------------------------------------------

def summary(db_path=None):
    """The Investment Dashboard 'Overview' numbers, computed from the
    canonical tables. Realized P&L keeps 5003's definition (closed equity +
    closed MF journals) so SELLs that shrink open positions are not
    double-counted."""
    holdings = compute_holdings(db_path)
    conn = _db(db_path)
    realized_eq = conn.execute("SELECT COALESCE(SUM(net_pl),0) FROM inv_closed_equity").fetchone()[0]
    realized_mf = conn.execute(
        "SELECT COALESCE(SUM(net_pl),0) FROM inv_fund_positions WHERE status='CLOSED'"
    ).fetchone()[0]
    closed_eq_count = conn.execute("SELECT COUNT(*) FROM inv_closed_equity").fetchone()[0]
    closed_mf_count = conn.execute(
        "SELECT COUNT(*) FROM inv_fund_positions WHERE status='CLOSED'"
    ).fetchone()[0]
    div_row = conn.execute(
        "SELECT COALESCE(SUM(per_share*qty),0), COALESCE(SUM(per_share*qty*tax_pct/100.0),0), "
        "COUNT(*) FROM inv_dividends"
    ).fetchone()
    fund_open = conn.execute(
        "SELECT COALESCE(SUM(units*COALESCE(current_nav, entry_nav)),0), "
        "COALESCE(SUM(cost_basis),0), COUNT(*) "
        "FROM inv_fund_positions WHERE status='OPEN'"
    ).fetchone()
    conn.close()

    div_gross, div_tax, div_count = div_row
    div_net = div_gross - div_tax
    cost_basis = holdings["totals"]["cost_basis"]
    unrealized_pl = holdings["totals"]["unrealized_pl"]
    realized_total = realized_eq + realized_mf
    total_return = unrealized_pl + realized_total + div_net
    fund_value = fund_open[0]

    allocation = [
        {"ticker": h["ticker"], "value": h["market_value"]}
        for h in holdings["holdings"] if h["market_value"] > 0
    ]
    alloc_total = sum(a["value"] for a in allocation)
    for a in allocation:
        a["pct"] = (a["value"] / alloc_total * 100) if alloc_total else 0.0

    return {
        "portfolio_value": holdings["totals"]["market_value"],
        "equity_cost_basis": cost_basis,
        "unrealized_pl": unrealized_pl,
        "unrealized_pct": holdings["totals"]["unrealized_pct"],
        "realized_equity_pl": realized_eq,
        "realized_fund_pl": realized_mf,
        "realized_pl": realized_total,
        "closed_equity_count": closed_eq_count,
        "closed_fund_count": closed_mf_count,
        "dividends_gross": div_gross,
        "dividends_tax": div_tax,
        "dividends_net": div_net,
        "dividend_count": div_count,
        "fund_open_value": fund_value,
        "fund_open_cost": fund_open[1],
        "fund_open_count": fund_open[2],
        "total_return": total_return,
        "total_return_pct": (total_return / cost_basis * 100) if cost_basis else 0.0,
        "allocation": allocation,
        "open_positions": len(holdings["holdings"]),
        "fees": {"buy_fee_pct": BUY_FEE * 100, "sell_fee_pct": SELL_FEE * 100,
                 "default_div_tax_pct": DEFAULT_DIV_TAX_PCT},
    }


# ---------------------------------------------------------------------------
# import / export (5003 snapshot shape)
# ---------------------------------------------------------------------------

def import_snapshot(payload, db_path=None):
    """Import an Investment Dashboard snapshot ({txns, CEQ, mfOpen, CMF,
    divs, eqPrices}) into the canonical tables. Idempotent: rows are keyed by
    their natural/declared identities, so re-running the same snapshot adds
    nothing. Returns the counts of rows actually added/upserted."""
    counts = {"transactions": 0, "closed_equity": 0, "funds": 0, "dividends": 0, "prices": 0}

    for t in payload.get("txns") or []:
        # external_id = the 5003 record id: legitimate same-day identical
        # fills exist in the source, so idempotency keys on that id, not on
        # the natural columns.
        txn_id = add_transaction(t.get("date"), t.get("ticker"), t.get("type"),
                                 t.get("price"), t.get("qty"), t.get("notes") or "",
                                 db_path=db_path, external_id=f"txn-{t.get('id')}")
        if txn_id is not None:
            counts["transactions"] += 1

    for c in payload.get("CEQ") or []:
        counts["closed_equity"] += add_closed_equity(
            c.get("entryDate"), c.get("exitDate"), c.get("ticker"),
            c.get("entryPrice"), c.get("exitPrice"), c.get("qty"),
            c.get("netPL"), c.get("plPct"), db_path=db_path)

    funds = [{"status": "OPEN", **f} for f in (payload.get("mfOpen") or [])]
    closed = [{"status": "CLOSED", **f} for f in (payload.get("CMF") or [])]

    conn = _db(db_path)
    for f in funds + closed:
        status = f["status"]
        fund_id = str(f.get("id") or f"{f.get('name', 'fund')}-{f.get('entryDate', '')}")
        conn.execute(
            "INSERT INTO inv_fund_positions (id, name, status, entry_date, exit_date, entry_nav, "
            "exit_nav, units, cost_basis, current_nav, total_return, net_pl, pl_pct) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET name=excluded.name, status=excluded.status, "
            "entry_date=excluded.entry_date, exit_date=excluded.exit_date, entry_nav=excluded.entry_nav, "
            "exit_nav=excluded.exit_nav, units=excluded.units, cost_basis=excluded.cost_basis, "
            "current_nav=excluded.current_nav, total_return=excluded.total_return, "
            "net_pl=excluded.net_pl, pl_pct=excluded.pl_pct",
            (fund_id, str(f.get("name") or fund_id), status, _norm_date(f.get("entryDate")),
             _norm_date(f["exitDate"]) if f.get("exitDate") else None,
             float(f.get("entryNav") or 0), float(f["exitNav"]) if f.get("exitNav") is not None else None,
             float(f.get("units") or 0), float(f.get("costBasis") or 0),
             float(f["currentNav"]) if f.get("currentNav") is not None else None,
             float(f["totalReturn"]) if f.get("totalReturn") is not None else None,
             float(f["netPL"]) if f.get("netPL") is not None else None,
             float(f["plPct"]) if f.get("plPct") is not None else None),
        )
        counts["funds"] += 1
    conn.commit()
    conn.close()

    for d in payload.get("divs") or []:
        counts["dividends"] += add_dividend(
            d.get("date"), d.get("ticker"), d.get("perShare"), d.get("qty"),
            d.get("taxPct", DEFAULT_DIV_TAX_PCT), d.get("notes") or "",
            db_path=db_path, external_id=f"div-{d.get('id')}")

    for ticker, price in (payload.get("eqPrices") or {}).items():
        set_price(ticker, price, source="manual", db_path=db_path)
        counts["prices"] += 1

    return counts


def export_snapshot(db_path=None):
    """Round-trip shape compatible with 5003's export/import JSON."""
    conn = _db(db_path)
    txns = [
        {"id": r[0], "date": r[1], "ticker": r[2], "type": r[3], "price": r[4], "qty": r[5],
         "notes": r[6]}
        for r in conn.execute(
            "SELECT id, date, ticker, type, price, qty, notes FROM inv_transactions ORDER BY id")
    ]
    ceq = [
        {"id": r[0], "entryDate": r[1], "exitDate": r[2], "ticker": r[3], "entryPrice": r[4],
         "exitPrice": r[5], "qty": r[6], "netPL": r[7], "plPct": r[8]}
        for r in conn.execute(
            "SELECT id, entry_date, exit_date, ticker, entry_price, exit_price, qty, net_pl, pl_pct "
            "FROM inv_closed_equity ORDER BY id")
    ]
    mf_open, mf_closed = [], []
    for r in conn.execute(
            "SELECT id, name, status, entry_date, exit_date, entry_nav, exit_nav, units, "
            "cost_basis, current_nav, total_return, net_pl, pl_pct FROM inv_fund_positions ORDER BY id"):
        rec = {"id": r[0], "name": r[1], "entryDate": r[3], "entryNav": r[5], "units": r[7],
               "costBasis": r[8]}
        if r[2] == "CLOSED":
            rec.update({"exitDate": r[4], "exitNav": r[6], "totalReturn": r[10],
                        "netPL": r[11], "plPct": r[12]})
            mf_closed.append(rec)
        else:
            if r[9] is not None:
                rec["currentNav"] = r[9]
            mf_open.append(rec)
    divs = [
        {"id": r[0], "date": r[1], "ticker": r[2], "perShare": r[3], "qty": r[4],
         "taxPct": r[5], "notes": r[6]}
        for r in conn.execute(
            "SELECT id, date, ticker, per_share, qty, tax_pct, notes FROM inv_dividends ORDER BY id")
    ]
    prices = {r[0]: r[1] for r in conn.execute("SELECT ticker, price FROM inv_prices")}
    conn.close()
    return {"txns": txns, "CEQ": ceq, "mfOpen": mf_open, "CMF": mf_closed,
            "divs": divs, "eqPrices": prices}
