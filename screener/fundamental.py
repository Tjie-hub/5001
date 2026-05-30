"""
screener/fundamental.py — Fundamental screener query engine
============================================================
Used by: screener/routes.py (Flask API) and screener_clone.py (CLI)
"""
import sqlite3

from config import DB_PATH

COLUMNS = {
    "ticker":        ("k", "ticker",       "text",     "Ticker"),
    "pe_ttm":        ("k", "pe_ttm",       "float",    "PE (TTM)"),
    "pe_ann":        ("k", "pe_ann",       "float",    "PE (Annual)"),
    "pe_forward":    ("k", "pe_forward",   "float",    "PE (Forward)"),
    "pbv":           ("k", "pbv",          "float",    "PBV"),
    "ps_ttm":        ("k", "ps_ttm",       "float",    "P/S (TTM)"),
    "eps_ttm":       ("k", "eps_ttm",      "float",    "EPS (TTM)"),
    "bvps":          ("k", "bvps",         "float",    "BVPS"),
    "earnings_yield":("k", "earnings_yield","float",   "Earnings Yield"),
    "pcf_ttm":       ("k", "pcf_ttm",      "float",    "P/CF (TTM)"),
    "pfcf_ttm":      ("k", "pfcf_ttm",     "float",    "P/FCF (TTM)"),
    "ev_ebit":       ("k", "ev_ebit",      "float",    "EV/EBIT"),
    "ev_ebitda":     ("k", "ev_ebitda",    "float",    "EV/EBITDA"),
    "peg_ratio":     ("k", "peg_ratio",    "float",    "PEG Ratio"),
    "fcf_per_share": ("k", "fcf_per_share","float",    "FCF/Share"),
    "cash_per_share":("k", "cash_per_share","float",   "Cash/Share"),
    "revenue_per_share":("k", "revenue_per_share","float","Revenue/Share"),
    "current_ratio": ("k", "current_ratio","float",    "Current Ratio"),
    "quick_ratio":   ("k", "quick_ratio",  "float",    "Quick Ratio"),
    "roe":           ("k", "roe",          "float",    "ROE (%)"),
    "roa":           ("k", "roa",          "float",    "ROA (%)"),
    "der":           ("k", "der",          "float",    "D/E Ratio"),
    "npm":           ("k", "npm",          "float",    "Net Profit Margin (%)"),
    "div_yield":     ("k", "div_yield",    "float",    "Dividend Yield (%)"),
    "rev_growth":    ("k", "rev_growth",   "float",    "Revenue Growth (%)"),
    "earn_growth":   ("k", "earn_growth",  "float",    "Earnings Growth (%)"),
    "flow_score":    ("f", "composite_score","int",    "Flow Score"),
    "flow_verdict":  ("f", "verdict",       "text",    "Flow Verdict"),
    "smart_money":   ("f", "smart_money",   "text",    "Smart Money"),
    "net_lot":       ("f", "net_lot",       "int",     "Net Lots"),
    "net_value":     ("f", "net_value",     "int",     "Net Value (IDR)"),
    "last_price":    ("f", "last_price",    "int",     "Last Price"),
    "buy_lot":       ("f", "buy_lot",       "int",     "Buy Lots"),
    "sell_lot":      ("f", "sell_lot",      "int",     "Sell Lots"),
    "in_idx30":      ("i", "in_idx30",      "int",     "IDX30"),
    "in_lq45":       ("i", "in_lq45",       "int",     "LQ45"),
    "in_idx80":      ("i", "in_idx80",      "int",     "IDX80"),
}

UNIVERSE = {
    "ALL":    "",
    "IDX30":  "AND i.in_idx30 = 1",
    "LQ45":   "AND i.in_lq45 = 1",
    "IDX80":  "AND i.in_idx80 = 1",
    "NON_IDX":"AND i.in_idx80 = 0 AND i.in_lq45 = 0 AND i.in_idx30 = 0",
}

DEFAULT_COLUMNS = ["ticker", "pe_ttm", "pbv", "roe", "der", "npm", "rev_growth", "flow_score", "flow_verdict"]


def run_query(columns, universe="ALL", filters="", sort="ticker", sort_dir="ASC", page=1, perpage=20, db_path=None, ticker_filter=None):
    """Execute a fundamental screener query. Returns dict with total, page, results, columns."""
    if db_path is None:
        db_path = DB_PATH

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Validate columns
    selected = []
    tables = set()
    col_map = {}

    for col in columns:
        if col not in COLUMNS:
            continue
        table, field, col_type, label = COLUMNS[col]
        alias = f"{table}_{field}"
        selected.append(f"{table}.{field} AS {alias}")
        col_map[col] = {"alias": alias, "type": col_type, "label": label, "table": table, "field": field}
        tables.add(table)

    if not selected:
        conn.close()
        return {"total": 0, "page": page, "perpage": perpage, "total_pages": 0, "columns": [], "results": []}

    # Build joins
    joins = []
    if "k" in tables:
        joins.append(
            "LEFT JOIN (SELECT *, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY fetch_date DESC) AS rn "
            "FROM stockbit_keystats) k ON i.ticker = k.ticker AND k.rn = 1"
        )
    if "f" in tables:
        joins.append(
            "LEFT JOIN (SELECT *, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY trade_date DESC) AS rn "
            "FROM stockbit_flow WHERE composite_score IS NOT NULL) f ON i.ticker = f.ticker AND f.rn = 1"
        )

    where = "WHERE i.status = 'active'"
    if universe in UNIVERSE and UNIVERSE[universe]:
        where += " " + UNIVERSE[universe]
    ticker_params = []
    if ticker_filter:
        placeholders = ",".join("?" * len(ticker_filter))
        where += f" AND i.ticker IN ({placeholders})"
        ticker_params = list(ticker_filter)

    # Parse filters
    filter_clauses = []
    if filters:
        for f in filters.split(";"):
            f = f.strip()
            if not f:
                continue
            for op in [">=", "<=", "!=", ">", "<", "="]:
                if op in f:
                    col, val = f.split(op, 1)
                    col = col.strip()
                    val = val.strip()
                    if col in COLUMNS:
                        table, field, col_type, _ = COLUMNS[col]
                        if col_type in ("float", "int"):
                            try:
                                float(val)
                            except ValueError:
                                continue
                        else:
                            val = f"'{val}'"
                        filter_clauses.append(f"{table}.{field} {op} {val}")
                    break

    query = f"""
        SELECT {', '.join(selected)}
        FROM idx_tickers i
        {' '.join(joins)}
        {where}
        {'AND ' + ' AND '.join(filter_clauses) if filter_clauses else ''}
    """

    # Sorting
    if sort and sort in COLUMNS:
        table, field, _, _ = COLUMNS[sort]
        sort_clause = f"{table}.{field} {sort_dir}"
    else:
        sort_clause = "i.ticker ASC"

    query += f" ORDER BY {sort_clause}"

    # Count
    count_sql = query.replace(f"SELECT {', '.join(selected)}", "SELECT COUNT(*)")
    count_sql = count_sql[:count_sql.rfind("ORDER BY")]
    total = conn.execute(count_sql, ticker_params).fetchone()[0]

    # Paginate
    offset = (page - 1) * perpage
    query += f" LIMIT {perpage} OFFSET {offset}"

    rows = conn.execute(query, ticker_params).fetchall()
    conn.close()

    results = []
    for row in rows:
        item = {}
        for c in columns:
            if c in col_map:
                item[c] = row[col_map[c]["alias"]]
        results.append(item)

    col_info = [{"key": c, "label": col_map[c]["label"], "type": col_map[c]["type"]} for c in columns if c in col_map]

    return {
        "total": total,
        "page": page,
        "perpage": perpage,
        "total_pages": max(1, -(-total // perpage)),
        "columns": col_info,
        "results": results,
    }
