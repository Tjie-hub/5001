"""routes/portfolio.py — Portfolio backtest API."""
import logging

from flask import Blueprint, jsonify, request

from config import DB_PATH
from engine.sector_rotation import IDX_SECTOR_MAP
from engine.walkforward_multi import STRATEGY_FUNCS
from engine.portfolio_backtest import run_portfolio_backtest

portfolio_bp = Blueprint('portfolio', __name__)


@portfolio_bp.route('/api/portfolio/sectors', methods=['GET'])
def api_portfolio_sectors():
    return jsonify({'sectors': {k: list(v) for k, v in IDX_SECTOR_MAP.items()}})


@portfolio_bp.route('/api/portfolio/backtest', methods=['POST'])
def api_portfolio_backtest():
    body = request.get_json(force=True) or {}
    sector   = body.get('sector', '')
    strategy = body.get('strategy', 'vol_weighted')
    capital  = float(body.get('capital', 50_000_000))

    if sector not in IDX_SECTOR_MAP:
        return jsonify({'error': f'Unknown sector: {sector}'}), 400
    if strategy not in STRATEGY_FUNCS:
        return jsonify({'error': f'Unknown strategy: {strategy}'}), 400
    if capital <= 0:
        return jsonify({'error': 'capital must be > 0'}), 400

    tickers = list(IDX_SECTOR_MAP[sector])
    try:
        result = run_portfolio_backtest(tickers, strategy, capital, DB_PATH)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception:
        logging.exception('portfolio backtest error')
        return jsonify({'error': 'internal error'}), 500

    return jsonify({'sector': sector, 'strategy': strategy, 'capital': capital, **result})
