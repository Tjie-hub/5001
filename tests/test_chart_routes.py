import sqlite3
import pytest
from unittest import mock


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "wf.db"
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL,
        high REAL, low REAL, close REAL, volume REAL, UNIQUE(ticker,date))""")
    conn.execute("""CREATE TABLE stockbit_flow_bars (ticker TEXT, trade_date TEXT,
        bar_time TEXT, buy_lot INT, sell_lot INT, buy_freq INT, sell_freq INT,
        net_value INT, price INT, delta INT,
        PRIMARY KEY(ticker,trade_date,bar_time))""")
    import pandas as pd
    for i, d in enumerate(pd.date_range('2026-03-01', periods=40, freq='D')):
        conn.execute("INSERT INTO ohlcv VALUES (?,?,?,?,?,?,?)",
                     ('BBCA', d.strftime('%Y-%m-%d'), 100, 105, 95, 100 + i % 5, 1000))
    conn.execute("INSERT INTO stockbit_flow_bars VALUES (?,?,?,?,?,?,?,?,?,?)",
                 ('BBCA', '2026-06-15', '09:00', 100, 40, 5, 3, 1000, 100, 60))
    conn.commit(); conn.close()

    monkeypatch.setenv('DB_PATH', str(db))
    import importlib, config
    importlib.reload(config)
    import engine.delta_flow as df_mod
    importlib.reload(df_mod)
    from routes import chart as chart_mod
    importlib.reload(chart_mod)

    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(chart_mod.chart_bp)
    return app.test_client(), chart_mod


def test_indicators_bundle_shape(client):
    c, _ = client
    r = c.get('/api/chart/BBCA/indicators?tf=D&inds=vp,fvg,sr,vwap,vwma,patterns')
    assert r.status_code == 200
    j = r.get_json()
    assert 'vp' in j and 'fvg' in j and 'sr' in j
    assert 'vwap' in j and 'vwma' in j and 'patterns' in j


def test_delta_bundle_shape(client):
    c, _ = client
    r = c.get('/api/chart/BBCA/delta?date=2026-06-15&parts=cvd,bars,profile,stats')
    assert r.status_code == 200
    j = r.get_json()
    assert j['cvd'][0]['cvd'] == 60
    assert j['stats']['total_delta'] == 60


def test_tv_sync_calls_bridge(client):
    c, mod = client
    with mock.patch.object(mod.tv_bridge, 'set_symbol',
                           return_value={'ok': True, 'symbol': 'BBCA'}) as m:
        r = c.post('/api/chart/tv/sync', json={'symbol': 'BBCA'})
    assert r.status_code == 200 and r.get_json()['ok'] is True
    m.assert_called_once_with('BBCA')


def test_tv_status(client):
    c, mod = client
    with mock.patch.object(mod.tv_bridge, 'is_available', return_value=False):
        r = c.get('/api/chart/tv/status')
    assert r.get_json()['available'] is False
