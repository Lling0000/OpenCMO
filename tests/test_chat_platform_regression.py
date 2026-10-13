from __future__ import annotations

import json

import pytest
import requests

from opencmo.ops.chat_platform_regression import (
    DEFAULT_CASES,
    PlatformCase,
    _iter_sse_payloads,
    main,
    run_case,
    select_cases,
)


def test_select_cases_returns_all_by_default():
    cases = select_cases(None)
    assert cases == list(DEFAULT_CASES)


def test_select_cases_filters_case_insensitively():
    cases = select_cases(["twitter", "InfoQ"])
    assert [case.platform for case in cases] == ["Twitter", "InfoQ"]


def test_iter_sse_payloads_parses_data_lines_and_stops_on_done():
    class FakeResponse:
        def iter_lines(self, decode_unicode=True):
            assert decode_unicode is True
            yield "data: " + json.dumps({"type": "agent", "name": "Twitter Expert"})
            yield ""
            yield "data: " + json.dumps({"type": "done", "final_output": "ok"})
            yield "data: " + json.dumps({"type": "delta", "content": "ignored"})

    events = list(_iter_sse_payloads(FakeResponse()))
    assert events == [
        {"type": "agent", "name": "Twitter Expert"},
        {"type": "done", "final_output": "ok"},
        {"type": "delta", "content": "ignored"},
    ]


def test_run_case_returns_error_when_session_creation_fails():
    class FailingSession:
        def post(self, *_args, **_kwargs):
            raise RuntimeError("boom")

    result = run_case(
        FailingSession(),
        base_url="https://example.com/api/v1",
        project_id=36,
        locale="zh",
        case=PlatformCase("Twitter", "write", "Twitter Expert"),
        connect_timeout=5,
        read_timeout=5,
    )

    assert result["platform"] == "Twitter"
    assert result["done"] is False
    assert result["error"].startswith("session_create_failed:")


def test_main_requires_auth_before_any_request(monkeypatch, capsys):
    monkeypatch.delenv("OPENCMO_WEB_TOKEN", raising=False)

    def unexpected_request(*_args, **_kwargs):
        pytest.fail("Missing authentication must not make network requests")

    monkeypatch.setattr(requests.Session, "request", unexpected_request)
    assert main(["--project-id", "36", "--platform", "Twitter", "--json", "--require-auth"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["done"] is False
    assert "authentication_not_configured" in result["error"]


@pytest.mark.parametrize(
    ("status", "events", "expected_exit", "expected_error"),
    [
        (200, [{"type": "agent", "name": "Twitter Expert"}, {"type": "done", "final_output": "ok"}], 0, None),
        (401, [], 1, "401 Client Error"),
        (200, [{"type": "agent", "name": "Wrong Expert"}, {"type": "done"}], 1, None),
        (200, [{"type": "agent", "name": "Twitter Expert"}], 1, None),
        (200, [{"type": "agent", "name": "Twitter Expert"}, {"type": "done", "stream_timed_out": True}], 1, None),
        (200, [{"type": "error", "message": "model unavailable"}], 1, "model unavailable"),
    ],
)
def test_main_authenticated_session_and_stream_results(monkeypatch, capsys, status, events, expected_exit, expected_error):
    """Use real requests preparation to verify the session header on both POSTs."""
    token = "test-only-workspace-credential"
    monkeypatch.setenv("OPENCMO_WEB_TOKEN", token)
    calls = []

    def send(_adapter, request, **_kwargs):
        calls.append(request)
        assert request.headers["Authorization"] == f"Bearer {token}"
        response = requests.Response()
        response.url = request.url
        response.request = request
        response.status_code = 200 if request.url.endswith("/chat/sessions") else status
        response.encoding = "utf-8"
        response._content = (
            b'{"session_id": "test-session"}' if request.url.endswith("/chat/sessions") else
            "\n".join("data: " + json.dumps(event) for event in events).encode()
        )
        response._content_consumed = True
        return response

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    exit_code = main([
        "--base-url", "https://example.com/api/v1", "--project-id", "36", "--platform", "Twitter",
        "--json", "--require-auth", "--fail-on-incomplete",
    ])
    assert exit_code == expected_exit
    output = capsys.readouterr().out
    assert token not in output
    result = json.loads(output)
    assert len(calls) == 2
    assert calls[1].headers["Accept"] == "text/event-stream"
    if expected_error:
        assert expected_error in result["error"]
    else:
        assert result["error"] is None
