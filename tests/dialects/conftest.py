"""Dialect test harness helpers."""

from __future__ import annotations

import signal

import pytest


@pytest.fixture(autouse=True)
def _dialect_parse_wall_clock_guard(request):
    """
    Fail dialect tests that hang in parse loops instead of blocking CI indefinitely.

    Unix only (SIGALRM). Skipped on platforms without alarm support.
    """
    if not hasattr(signal, "SIGALRM"):
        yield
        return

    timeout_s = 5

    def _on_alarm(signum, frame):
        raise TimeoutError(
            f"{request.node.nodeid} exceeded {timeout_s}s — possible parser infinite loop"
        )

    previous = signal.signal(signal.SIGALRM, _on_alarm)
    signal.alarm(timeout_s)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
