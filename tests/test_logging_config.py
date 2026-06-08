"""Tests for utils/logging_config.py — R13 structured JSON logging."""
import json
import logging
import tempfile
import os
import pytest


def _capture_json(msg='hello', level=logging.INFO, extra=None):
    """Emit a single log record through JSONFormatter, return parsed dict."""
    from utils.logging_config import JSONFormatter, CorrelationFilter
    import io
    handler = logging.StreamHandler(io.StringIO())
    handler.setFormatter(JSONFormatter())
    handler.addFilter(CorrelationFilter())
    logger = logging.getLogger(f'test_{id(handler)}')
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    if extra:
        logger.log(level, msg, extra=extra)
    else:
        logger.log(level, msg)
    handler.stream.seek(0)
    return json.loads(handler.stream.read())


class TestJSONFormatter:
    def test_required_keys_present(self):
        rec = _capture_json('test message')
        assert {'time', 'level', 'logger', 'msg'} <= set(rec.keys())

    def test_message_content(self):
        rec = _capture_json('hello world')
        assert rec['msg'] == 'hello world'

    def test_level_name(self):
        assert _capture_json(level=logging.WARNING)['level'] == 'WARNING'
        assert _capture_json(level=logging.ERROR)['level'] == 'ERROR'

    def test_extra_fields_included(self):
        rec = _capture_json('msg', extra={'duration_ms': 42, 'status': 200})
        assert rec.get('duration_ms') == 42
        assert rec.get('status') == 200

    def test_time_is_iso(self):
        rec = _capture_json('x')
        t = rec['time']
        assert 'T' in t and ('+' in t or 'Z' in t or t.endswith('Z'))

    def test_exception_info_included(self):
        from utils.logging_config import JSONFormatter, CorrelationFilter
        import io
        handler = logging.StreamHandler(io.StringIO())
        handler.setFormatter(JSONFormatter())
        logger = logging.getLogger('exc_test')
        logger.handlers = [handler]
        logger.propagate = False
        try:
            raise ValueError('boom')
        except ValueError:
            logger.exception('caught it')
        handler.stream.seek(0)
        rec = json.loads(handler.stream.read())
        assert 'exc' in rec
        assert 'ValueError' in rec['exc']


class TestCorrelationFilter:
    def test_no_correlation_id_outside_request(self):
        from utils.logging_config import CorrelationFilter
        CorrelationFilter._thread_local_id = None
        rec = _capture_json('msg')
        assert rec.get('correlation_id') is None

    def test_thread_local_id_injected(self):
        from utils.logging_config import CorrelationFilter, set_correlation_id
        cid = set_correlation_id('test-123')
        rec = _capture_json('msg')
        CorrelationFilter._thread_local_id = None  # clean up
        assert rec.get('correlation_id') == 'test-123'


class TestSetupLogging:
    def test_creates_log_directory(self):
        from utils.logging_config import setup_logging
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, 'logs')
            setup_logging(log_dir=log_dir)
            assert os.path.isdir(log_dir)

    def test_log_file_created(self):
        from utils.logging_config import setup_logging
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, 'logs')
            setup_logging(log_dir=log_dir)
            logging.info('test log entry')
            log_file = os.path.join(log_dir, 'app.log')
            assert os.path.exists(log_file)
            with open(log_file) as f:
                lines = [l for l in f.readlines() if l.strip()]
            assert any('test log entry' in l for l in lines)
