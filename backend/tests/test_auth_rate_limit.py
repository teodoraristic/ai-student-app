"""Login rate limiting (in-process, per IP)."""

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import backend.routers.auth as auth_router


def _make_request(client_host: str = "203.0.113.42") -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "POST",
            "path": "/auth/login",
            "raw_path": b"/auth/login",
            "root_path": "",
            "scheme": "http",
            "query_string": b"",
            "headers": [],
            "client": (client_host, 54321),
            "server": ("testserver", 80),
        }
    )


@pytest.fixture(autouse=True)
def _clear_login_failures() -> None:
    auth_router._login_fail_times.clear()
    yield
    auth_router._login_fail_times.clear()


class TestLoginRateLimit:
    def test_allows_failures_below_cap(self) -> None:
        req = _make_request("198.51.100.1")
        for _ in range(14):
            auth_router._record_login_failure(req)
        auth_router._enforce_login_rate_limit(req)

    def test_blocks_after_max_failures(self) -> None:
        req = _make_request("198.51.100.2")
        for _ in range(15):
            auth_router._record_login_failure(req)
        with pytest.raises(HTTPException) as exc:
            auth_router._enforce_login_rate_limit(req)
        assert exc.value.status_code == 429

    def test_success_clears_failures_for_ip(self) -> None:
        req = _make_request("198.51.100.3")
        for _ in range(14):
            auth_router._record_login_failure(req)
        auth_router._clear_login_failures(req)
        auth_router._enforce_login_rate_limit(req)
        for _ in range(14):
            auth_router._record_login_failure(req)
        auth_router._enforce_login_rate_limit(req)

    def test_independent_buckets_per_ip(self) -> None:
        a = _make_request("198.51.100.10")
        b = _make_request("198.51.100.11")
        for _ in range(15):
            auth_router._record_login_failure(a)
        auth_router._enforce_login_rate_limit(b)
