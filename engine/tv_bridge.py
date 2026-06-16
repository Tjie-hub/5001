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
_TIMEOUT = 4          # HTTP probe / handshake
_EVAL_TIMEOUT = 10    # Runtime.evaluate may be slow while the chart reloads


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
    """Pick the TradingView *chart* page's debugger websocket URL.

    TradingView Desktop (Electron) exposes many pages, several of whose
    file:// URLs contain the substring 'tradingview' (e.g. the snap path
    file:///snap/tradingview/...). The real chart — the only context where
    window.TradingViewApi exists — is served from the tradingview.com web
    origin, so match on that domain and prefer the '/chart' page.
    """
    pages = [p for p in _http_json('/json') if p.get('type') == 'page'
             and p.get('webSocketDebuggerUrl')]
    web = [p for p in pages if 'tradingview.com' in (p.get('url') or '').lower()]
    for p in web:
        if '/chart' in (p.get('url') or '').lower():
            return p['webSocketDebuggerUrl']
    if web:
        return web[0]['webSocketDebuggerUrl']
    raise ConnectionError('no tradingview.com chart page found on CDP')


def _cdp_evaluate(ws_url: str, expression: str) -> dict:
    """Send Runtime.evaluate over the CDP websocket. Requires websocket-client."""
    import websocket  # lazy import; optional dependency
    # Chrome/Electron CDP rejects WS connections whose Origin header is not in
    # its allowlist (403). websocket-client derives an Origin from the URL by
    # default; suppress it so the handshake is accepted (matches how the
    # Node chrome-remote-interface client connects).
    ws = websocket.create_connection(ws_url, timeout=_EVAL_TIMEOUT, suppress_origin=True)
    try:
        ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate',
                            'params': {'expression': expression,
                                       'returnByValue': True}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get('id') == 1:
                # Surface a JS-side error (e.g. evaluating on a page where
                # window.TradingViewApi is undefined) instead of silently
                # reporting success.
                if 'error' in msg:
                    raise RuntimeError(msg['error'].get('message', 'CDP error'))
                exc = msg.get('result', {}).get('exceptionDetails')
                if exc:
                    raise RuntimeError(exc.get('text', 'JS exception') + ': '
                                       + str(exc.get('exception', {}).get('description', '')))
                return msg.get('result', {})
    finally:
        ws.close()


def _safe_symbol(symbol: str) -> str:
    """Allow only ticker-safe chars (letters, digits, :, ., -) and default
    the exchange to IDX when none is given (this is an IDX-only app), so a
    bare 'BBCA' from a signal click resolves to TradingView's 'IDX:BBCA'."""
    s = re.sub(r'[^A-Za-z0-9:.\-]', '', symbol or '').upper()
    if s and ':' not in s:
        s = 'IDX:' + s
    return s


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
