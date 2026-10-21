from types import SimpleNamespace

import pytest

from tests.backend.engine import helpers


@pytest.fixture
def elapsed_clock(monkeypatch):
    state = {"elapsed": 0.0, "wall": 1000.0}

    def sleep(duration):
        state["elapsed"] += duration
        state["wall"] += 3600

    monkeypatch.setattr(
        helpers,
        "time",
        SimpleNamespace(
            monotonic=lambda: state["elapsed"],
            time=lambda: state["wall"],
            sleep=sleep,
        ),
    )
    return state


def test_heartbeat_poll_ignores_a_forward_wall_clock_jump(elapsed_clock):
    client = SimpleNamespace(
        hget=lambda *_: "stale" if elapsed_clock["elapsed"] >= 0.2 else "idle"
    )
    assert helpers.wait_for_redis_hash_field_value(
        client, "worker", "status", "stale", timeout=0.3
    )
    assert elapsed_clock["elapsed"] == pytest.approx(0.2)


def test_wait_checks_readiness_at_the_deadline(elapsed_clock):
    assert helpers.wait_for_condition(
        lambda: elapsed_clock["elapsed"] >= 0.25, timeout=0.25
    )


def test_unsatisfied_wait_keeps_its_original_time_budget(elapsed_clock):
    assert not helpers.wait_for_condition(lambda: False, timeout=0.25)
    assert elapsed_clock["elapsed"] == pytest.approx(0.25)


def test_zero_timeout_still_checks_an_already_ready_condition(elapsed_clock):
    assert helpers.wait_for_condition(lambda: True, timeout=0)
    assert elapsed_clock["elapsed"] == 0
