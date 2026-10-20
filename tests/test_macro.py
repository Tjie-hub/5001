"""data/macro.py: BI page parsing, idempotent upsert, fail-soft fetch + scheduler job."""
from data import macro
from data.db import connect

BI_RATE_HTML = """<table><tr><td>No</td><td>Tanggal</td><td>BI-Rate</td></tr>
<tr><td>1</td><td>23 September 2026</td><td>5,75 %</td><td><a>Siaran Pers</a></td></tr>
<tr><td>2</td><td>9 Juni 2026</td><td>5,50 %</td></tr>
<script>var x = "1 Januari 2020 9,99 %";</script></table>"""

INFLATION_HTML = """<table><tr><td>Agustus 2026</td><td>3,19 %</td></tr>
<tr><td>Juli 2026</td><td>-0,12 %</td></tr></table>"""


def test_parse_bi_rate_reads_rows_and_ignores_scripts():
    assert macro.parse_bi_rate(BI_RATE_HTML) == [("2026-06-09", 5.50), ("2026-09-23", 5.75)]


def test_parse_bi_inflation_keeps_negative_sign():
    assert macro.parse_bi_inflation(INFLATION_HTML) == [("2026-07-01", -0.12), ("2026-08-01", 3.19)]


def test_upsert_is_idempotent_and_overwrites_value(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    macro.ensure_macro_table(conn)
    macro.ensure_macro_table(conn)  # safe to call twice
    macro.upsert(conn, [("vix", "2026-10-19", 18.0, "yahoo:^VIX")])
    macro.upsert(conn, [("vix", "2026-10-19", 18.44, "yahoo:^VIX")])
    assert conn.execute("SELECT count(*), max(value) FROM macro_daily").fetchone() == (1, 18.44)


def test_run_macro_fetch_stores_good_series_and_reports_failed(tmp_path):
    db = str(tmp_path / "t.db")
    ok = lambda: ([("sp500", "2026-10-19", 7690.73, "yahoo:^GSPC")], ["nickel"])  # noqa: E731
    bi = lambda: ([("bi_rate", "2026-09-23", 5.75, "bi.go.id")], [])  # noqa: E731
    res = macro.run_macro_fetch(db, fetchers=(ok, bi))
    assert res == {"rows": 2, "series": 2, "failed": ["nickel"]}
    assert connect(db).execute("SELECT count(*) FROM macro_daily").fetchone()[0] == 2


def test_series_keys_are_unique():
    keys = [k for k, *_ in macro.YAHOO_SERIES]
    assert len(keys) == len(set(keys))


def test_job_never_raises(monkeypatch):
    from scheduler import jobs
    sent = []
    monkeypatch.setattr(jobs, "send_telegram", lambda msg, **kw: sent.append(kw.get("event")))
    monkeypatch.setattr(macro, "run_macro_fetch", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    jobs.run_macro_fetch_job()
    assert sent == ["data.macro_fetch_fail"]
