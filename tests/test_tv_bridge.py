from unittest import mock
from engine import tv_bridge


def test_set_symbol_builds_expression_and_calls_cdp():
    captured = {}

    def fake_eval(ws_url, expression):
        captured['ws_url'] = ws_url
        captured['expr'] = expression
        return {'result': {'type': 'undefined'}}

    with mock.patch.object(tv_bridge, '_active_ws_url', return_value='ws://x/devtools/page/1'), \
         mock.patch.object(tv_bridge, '_cdp_evaluate', side_effect=fake_eval):
        res = tv_bridge.set_symbol('BBCA')
    assert res['ok'] is True
    assert 'setSymbol("BBCA"' in captured['expr']
    assert '_activeChartWidgetWV' in captured['expr']


def test_set_symbol_fail_open_when_cdp_down():
    with mock.patch.object(tv_bridge, '_active_ws_url',
                           side_effect=ConnectionError('refused')):
        res = tv_bridge.set_symbol('BBRI')
    assert res['ok'] is False
    assert 'reason' in res


def test_set_symbol_sanitizes_input():
    with mock.patch.object(tv_bridge, '_active_ws_url', return_value='ws://x/1'), \
         mock.patch.object(tv_bridge, '_cdp_evaluate', return_value={}) as ev:
        tv_bridge.set_symbol('BB"CA')  # quote must be stripped/escaped
    expr = ev.call_args[0][1]
    assert 'BB"CA' not in expr  # raw unescaped quote not injected
