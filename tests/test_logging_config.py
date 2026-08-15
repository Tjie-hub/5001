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


class TestRedactSecrets:
    """redact_secrets() — extracted (RC1 fix R-4) so log-line masking and
    outbound Telegram alerts share one implementation, not two."""

    def test_masks_configured_secret_value(self, monkeypatch):
        from utils.logging_config import redact_secrets
        monkeypatch.setenv("ZAI_API_KEY", "supersecretzaikey")
        assert redact_secrets("token=supersecretzaikey leaked") == "token=[REDACTED] leaked"

    def test_leaves_text_without_secrets_unchanged(self, monkeypatch):
        from utils.logging_config import redact_secrets
        monkeypatch.setenv("ZAI_API_KEY", "supersecretzaikey")
        assert redact_secrets("nothing sensitive here") == "nothing sensitive here"

    def test_ignores_values_shorter_than_8_chars(self, monkeypatch):
        from utils.logging_config import redact_secrets
        monkeypatch.setenv("AUTH_TOKEN_VIEWER", "short")
        assert redact_secrets("a short string") == "a short string"

    def test_handles_comma_separated_multi_value_vars(self, monkeypatch):
        from utils.logging_config import redact_secrets
        monkeypatch.setenv("AUTH_TOKEN_VIEWER", "firstlongtoken, secondlongtoken")
        text = redact_secrets("firstlongtoken and secondlongtoken both present")
        assert "firstlongtoken" not in text and "secondlongtoken" not in text

    def test_masks_stockbit_token_from_file(self, tmp_path, monkeypatch):
        """P1-5: the Stockbit JWT lives in .stockbit_token (a file), not an
        env var, so it was structurally invisible to the _SECRET_VARS loop
        no matter how it was configured."""
        import utils.logging_config as lc
        (tmp_path / ".stockbit_token").write_text("stockbitjwtvalue12345")
        monkeypatch.setattr(lc, "__file__",
                            str(tmp_path / "utils" / "logging_config.py"))
        text = lc.redact_secrets("Bearer stockbitjwtvalue12345 rejected")
        assert "stockbitjwtvalue12345" not in text
        assert "[REDACTED]" in text

    def test_missing_stockbit_token_file_is_not_an_error(self, tmp_path, monkeypatch):
        import utils.logging_config as lc
        monkeypatch.setattr(lc, "__file__",
                            str(tmp_path / "utils" / "logging_config.py"))
        assert lc.redact_secrets("clean text") == "clean text"


class TestRedactAndTruncate:
    """P1-5: truncate-before-redact ordering bug -- truncating raw exception
    text before redact_secrets() ever sees it can cut a secret mid-string, so
    the later redact_secrets() call inside send_telegram() no longer finds
    the *complete* value to match and a partial fragment survives."""

    def test_redacts_before_truncating(self, monkeypatch):
        from utils.logging_config import redact_and_truncate
        monkeypatch.setenv("ZAI_API_KEY", "supersecretzaikey1234567890")
        # The raw secret straddles the naive truncation boundary (char 20);
        # str(e)[:20] would leave "supersecretzaikey123" -- a still-partially
        # -identifying fragment -- unredacted.
        text = "prefix supersecretzaikey1234567890 suffix"
        result = redact_and_truncate(text, 20)
        assert "supersecretzaikey" not in result

    def test_truncates_to_the_given_limit(self, monkeypatch):
        from utils.logging_config import redact_and_truncate
        result = redact_and_truncate("x" * 500, 50)
        assert len(result) == 50

    def test_clean_text_behaves_like_plain_slicing(self, monkeypatch):
        from utils.logging_config import redact_and_truncate
        assert redact_and_truncate("hello world", 5) == "hello"


class TestSecretRedactionFilter:
    """The logging.Filter now delegates to redact_secrets() — verify the
    delegation actually redacts a log line (this filter had no direct test
    before RC1 fix R-4)."""

    def _emit(self, msg, extra_env, monkeypatch):
        from utils.logging_config import JSONFormatter, SecretRedactionFilter
        import io
        for k, v in extra_env.items():
            monkeypatch.setenv(k, v)
        handler = logging.StreamHandler(io.StringIO())
        handler.setFormatter(JSONFormatter())
        handler.addFilter(SecretRedactionFilter())
        logger = logging.getLogger(f'redact_test_{id(handler)}')
        logger.handlers = [handler]
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        logger.info(msg)
        handler.stream.seek(0)
        return json.loads(handler.stream.read())

    def test_filter_redacts_secret_in_log_message(self, monkeypatch):
        rec = self._emit("leaked token supersecretzaikey here",
                         {"ZAI_API_KEY": "supersecretzaikey"}, monkeypatch)
        assert "supersecretzaikey" not in rec["msg"]
        assert "[REDACTED]" in rec["msg"]

    def test_filter_leaves_clean_message_untouched(self, monkeypatch):
        rec = self._emit("all clear", {"ZAI_API_KEY": "supersecretzaikey"}, monkeypatch)
        assert rec["msg"] == "all clear"


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
