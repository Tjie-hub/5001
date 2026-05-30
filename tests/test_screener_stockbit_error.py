"""Tests for SB-1: stockbit_error propagation in /api/screener/fundamental."""
import json
import pytest
from unittest.mock import patch
from flask import Flask
from screener.routes import screener_bp

def _dummy():
    return {'results': [], 'columns': [], 'total': 0,
            'total_pages': 1, 'page': 1, 'perpage': 20}


@pytest.fixture()
def client():
    app = Flask(__name__)
    app.register_blueprint(screener_bp, url_prefix='/api/screener')
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def _get(client, template_id):
    with patch('screener.fundamental.run_query', side_effect=lambda **_: _dummy()):
        return client.get(f'/api/screener/fundamental?stockbit_template={template_id}')


# ── SB-1: error propagation ──────────────────────────────────────────────────

def test_stockbit_error_present_when_fetch_raises(client):
    with patch('screener.stockbit_screener.fetch_template_tickers',
               side_effect=Exception('token expired')), \
         patch('screener.fundamental.run_query', side_effect=lambda **_: _dummy()):
        resp = client.get('/api/screener/fundamental?stockbit_template=63')
    data = json.loads(resp.data)
    assert 'stockbit_error' in data


def test_stockbit_error_message_contains_reason(client):
    with patch('screener.stockbit_screener.fetch_template_tickers',
               side_effect=Exception('token expired')), \
         patch('screener.fundamental.run_query', side_effect=lambda **_: _dummy()):
        resp = client.get('/api/screener/fundamental?stockbit_template=63')
    data = json.loads(resp.data)
    assert 'token expired' in data['stockbit_error']


def test_stockbit_template_id_in_response_on_failure(client):
    with patch('screener.stockbit_screener.fetch_template_tickers',
               side_effect=Exception('bad id')), \
         patch('screener.fundamental.run_query', side_effect=lambda **_: _dummy()):
        resp = client.get('/api/screener/fundamental?stockbit_template=63')
    data = json.loads(resp.data)
    assert data.get('stockbit_template') == 63


def test_no_stockbit_error_on_success(client):
    with patch('screener.stockbit_screener.fetch_template_tickers',
               return_value=['BBCA', 'TLKM']), \
         patch('screener.fundamental.run_query', side_effect=lambda **_: _dummy()):
        resp = client.get('/api/screener/fundamental?stockbit_template=63')
    data = json.loads(resp.data)
    assert 'stockbit_error' not in data


def test_stockbit_ticker_count_present_on_success(client):
    with patch('screener.stockbit_screener.fetch_template_tickers',
               return_value=['BBCA', 'TLKM']), \
         patch('screener.fundamental.run_query', side_effect=lambda **_: _dummy()):
        resp = client.get('/api/screener/fundamental?stockbit_template=63')
    data = json.loads(resp.data)
    assert data.get('stockbit_ticker_count') == 2


def test_no_stockbit_fields_when_no_template(client):
    with patch('screener.fundamental.run_query', side_effect=lambda **_: _dummy()):
        resp = client.get('/api/screener/fundamental')
    data = json.loads(resp.data)
    assert 'stockbit_template' not in data
    assert 'stockbit_error' not in data
