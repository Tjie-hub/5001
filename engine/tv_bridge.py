"""Drive the TradingView Desktop chart over Chrome DevTools Protocol.

TV Desktop runs with remote debugging on port 9222. One job: set the
active chart symbol. Every public method is FAIL-OPEN — connection errors
return {'ok': False, 'reason': ...} and never raise into a Flask request.
"""
import json
import re
import urllib.request

CDP_HOST = 'localhost'
CDP_PORT = 9222
CHART_API = 'window.TradingViewApi._activeChartWidgetWV.value()'
_TIMEOUT = 4


def _http_json(path: str):
    url = f'http://{CDP_HOST}:{CDP_PORT}{path}'
    with urllib.request.urlopen(url, timeout=_TIMEOUT) as r:
        return json.loads(r.read().decode())


def is_available() -> bool:
    try:
        _http_json('/json/version')
        return True
    except Exception:
        return False


def _active_ws_url() -> str:
    """Pick the TradingView chart page's debugger websocket URL."""
    pages = _http_json('/json')
    for p in pages:
        if p.get('type') == 'page' and 'tradingview' in (p.get('url') or '').lower():
            return p['webSocketDebuggerUrl']
    # fall back to first page with a ws url
    for p in pages:
        if p.get('webSocketDebuggerUrl'):
            return p['webSocketDebuggerUrl']
    raise ConnectionError('no debuggable TradingView page found')


def _cdp_evaluate(ws_url: str, expression: str) -> dict:
    """Send Runtime.evaluate over the CDP websocket. Requires websocket-client."""
    import websocket  # lazy import; optional dependency
    ws = websocket.create_connection(ws_url, timeout=_TIMEOUT)
    try:
        ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate',
                            'params': {'expression': expression,
                                       'returnByValue': True}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get('id') == 1:
                return msg.get('result', {})
    finally:
        ws.close()


def _safe_symbol(symbol: str) -> str:
    """Allow only ticker-safe chars (letters, digits, :, ., -)."""
    return re.sub(r'[^A-Za-z0-9:.\-]', '', symbol or '').upper()


def set_symbol(symbol: str) -> dict:
    """Set the active TV Desktop chart symbol. Fail-open."""
    sym = _safe_symbol(symbol)
    if not sym:
        return {'ok': False, 'reason': 'empty/invalid symbol'}
    try:
        ws_url = _active_ws_url()
        expr = f'{CHART_API}.setSymbol("{sym}", {{}})'
        _cdp_evaluate(ws_url, expr)
        return {'ok': True, 'symbol': sym}
    except Exception as e:
        return {'ok': False, 'reason': str(e)}
