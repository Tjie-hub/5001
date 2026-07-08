from engine.agent_firm.providers.circuit_breaker import CircuitBreaker


def test_closed_allows_requests():
    cb = CircuitBreaker(failure_threshold=3, cooldown_s=30)
    assert cb.state == "CLOSED"
    assert cb.allow_request() is True


def test_opens_after_threshold_failures():
    cb = CircuitBreaker(failure_threshold=3, cooldown_s=30)
    assert cb.record_failure() is False  # 1st failure, still CLOSED
    assert cb.record_failure() is False  # 2nd failure, still CLOSED
    assert cb.record_failure() is True   # 3rd failure -> fresh OPEN transition
    assert cb.state == "OPEN"


def test_open_blocks_requests_before_cooldown():
    cb = CircuitBreaker(failure_threshold=1, cooldown_s=30)
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.allow_request() is False  # cooldown hasn't elapsed


def test_half_open_after_cooldown_allows_one_trial(monkeypatch):
    cb = CircuitBreaker(failure_threshold=1, cooldown_s=10)
    cb.record_failure()
    fake_now = [1000.0]
    monkeypatch.setattr(
        "engine.agent_firm.providers.circuit_breaker.time.monotonic",
        lambda: fake_now[0],
    )
    cb.last_failure = 990.0  # 10s ago, at/past cooldown
    assert cb.allow_request() is True
    assert cb.state == "HALF_OPEN"


def test_half_open_second_concurrent_caller_blocked_until_trial_resolves(monkeypatch):
    cb = CircuitBreaker(failure_threshold=1, cooldown_s=10)
    cb.record_failure()
    cb.last_failure = 0.0
    monkeypatch.setattr(
        "engine.agent_firm.providers.circuit_breaker.time.monotonic",
        lambda: 100.0,
    )
    assert cb.allow_request() is True   # first caller acquires the trial slot
    assert cb.allow_request() is False  # second concurrent caller is blocked


def test_trial_success_closes_circuit():
    cb = CircuitBreaker(failure_threshold=1, cooldown_s=0)
    cb.record_failure()
    cb.state = "HALF_OPEN"
    assert cb.record_success() is True  # was OPEN/HALF_OPEN -> now closed
    assert cb.state == "CLOSED"
    assert cb.consecutive_failures == 0


def test_trial_failure_reopens_circuit():
    cb = CircuitBreaker(failure_threshold=1, cooldown_s=0)
    cb.record_failure()
    cb.state = "HALF_OPEN"
    assert cb.record_failure() is True  # trial failed -> re-opens
    assert cb.state == "OPEN"


def test_release_trial_frees_slot_without_changing_state():
    cb = CircuitBreaker(failure_threshold=1, cooldown_s=10)
    cb.record_failure()
    cb.last_failure = 0.0
    import engine.agent_firm.providers.circuit_breaker as cb_mod
    orig = cb_mod.time.monotonic
    cb_mod.time.monotonic = lambda: 100.0
    try:
        assert cb.allow_request() is True  # acquires trial slot
        cb.release_trial()
        assert cb.allow_request() is True  # slot is free again
    finally:
        cb_mod.time.monotonic = orig
