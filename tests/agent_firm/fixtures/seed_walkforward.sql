-- Seed fixture: minimal OHLCV rows for BBRI used in agent_firm tests.
-- Mirrors production schema in data/walkforward.db.
-- Used as reference data; tests that need an actual DB use the tmp_db
-- fixture (conftest.py) or inline _seed() helpers.

CREATE TABLE IF NOT EXISTS ohlcv (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT    NOT NULL,
    date   TEXT    NOT NULL,
    open   REAL,
    high   REAL,
    low    REAL,
    close  REAL,
    volume REAL
);

INSERT INTO ohlcv (ticker, date, open, high, low, close, volume) VALUES
    ('BBRI', '2026-05-19', 3090.0, 3140.0, 3040.0, 3070.0, 318794703.0),
    ('BBRI', '2026-05-18', 3040.0, 3100.0, 3010.0, 3060.0, 348373200.0),
    ('BBRI', '2026-05-14', 3160.0, 3190.0, 3120.0, 3120.0, 297902969.0),
    ('BBRI', '2026-05-13', 3160.0, 3190.0, 3120.0, 3120.0, 243829837.0),
    ('BBRI', '2026-05-12', 3210.0, 3220.0, 3170.0, 3200.0, 152909038.0),
    ('BBRI', '2026-05-09', 3200.0, 3240.0, 3180.0, 3230.0, 189234100.0),
    ('BBRI', '2026-05-08', 3180.0, 3210.0, 3150.0, 3200.0, 201847500.0),
    ('BBRI', '2026-05-07', 3150.0, 3190.0, 3130.0, 3180.0, 178932400.0),
    ('BBRI', '2026-05-06', 3130.0, 3160.0, 3100.0, 3150.0, 165438200.0),
    ('BBRI', '2026-05-05', 3100.0, 3140.0, 3080.0, 3130.0, 143291700.0),
    ('BBRI', '2026-05-02', 3080.0, 3120.0, 3060.0, 3100.0, 132847600.0),
    ('BBRI', '2026-05-01', 3050.0, 3090.0, 3030.0, 3080.0, 121938400.0),
    ('BBRI', '2026-04-30', 3020.0, 3060.0, 3000.0, 3050.0, 118473200.0),
    ('BBRI', '2026-04-29', 3000.0, 3040.0, 2980.0, 3020.0, 109283700.0),
    ('BBRI', '2026-04-28', 2980.0, 3010.0, 2960.0, 3000.0, 103847500.0);
