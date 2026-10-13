"""No real network: exercise the same DNS pinning and streaming path as production."""
import asyncio
import socket
import time

import httpx
import pytest
import pytest_asyncio

from opencmo.tools import public_fetch


@pytest_asyncio.fixture
async def network(monkeypatch):
    requests = []
    resolved = []
    state = {"handler": lambda request: httpx.Response(200, text="# Public example text")}

    async def resolve(host, port, **kwargs):
        resolved.append(host)
        ip = host if host in {"127.0.0.1", "169.254.169.254", "::1"} else "93.184.216.34"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]

    async def handler(request):
        requests.append(request)
        result = state["handler"](request)
        if asyncio.iscoroutine(result):
            result = await result
        if result.is_stream_consumed:
            result = httpx.Response(result.status_code, headers=result.headers, stream=BytesStream(result.content))
        return result

    real_client = httpx.AsyncClient

    def client(**kwargs):
        assert kwargs["follow_redirects"] is False
        assert kwargs["trust_env"] is False
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", resolve)
    monkeypatch.setattr(public_fetch.httpx, "AsyncClient", client)
    return state, requests, resolved


@pytest.mark.asyncio
@pytest.mark.parametrize("url", [
    "http://localhost/a", "http://foo.local/a", "http://127.0.0.1/a",
    "http://169.254.169.254/latest/meta-data", "http://[::1]/a",
    "file:///etc/passwd", "https://user:password@example.com", "http://example.com:8081",
])
async def test_private_and_invalid_urls_never_connect(network, url):
    _, requests, _ = network
    with pytest.raises(ValueError):
        await public_fetch.fetch_public_text(url)
    assert requests == []


@pytest.mark.asyncio
async def test_dns_pinning_preserves_host_and_sni(network):
    _, requests, resolved = network
    response = await public_fetch.fetch_public_text("https://example.com/llms.txt")
    assert response.text == "# Public example text"
    assert response.url == "https://example.com/llms.txt"
    assert resolved == ["example.com"]
    assert requests[0].url.host == "93.184.216.34"
    assert requests[0].headers["host"] == "example.com"
    assert requests[0].extensions["sni_hostname"] == "example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize("blocked_ip", ["127.0.0.1", "224.0.0.1", "ff0e::1"])
async def test_mixed_public_private_dns_rejected(network, monkeypatch, blocked_ip):
    async def resolve(*args, **kwargs):
        return [(2, 1, 6, "", (ip, 443)) for ip in ("93.184.216.34", blocked_ip)]
    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", resolve)
    with pytest.raises(ValueError, match="private_url"):
        await public_fetch.fetch_public_text("https://example.com")
    assert network[1] == []


@pytest.mark.asyncio
async def test_redirect_to_private_never_connects(network):
    state, requests, _ = network
    state["handler"] = lambda request: httpx.Response(302, headers={"location": "http://127.0.0.1/secrets"})
    with pytest.raises(ValueError, match="private_url"):
        await public_fetch.fetch_public_text("https://example.com")
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_public_relative_redirect_and_loop_limit(network):
    state, requests, resolved = network
    state["handler"] = lambda request: (
        httpx.Response(302, headers={"location": "/llms.txt"})
        if request.url.path == "/" else httpx.Response(200, text="# redirected content")
    )
    assert (await public_fetch.fetch_public_text("https://example.com")).text == "# redirected content"
    assert resolved == ["example.com", "example.com"]
    requests.clear()
    state["handler"] = lambda request: httpx.Response(302, headers={"location": "/loop"})
    with pytest.raises(ValueError, match="too_many_redirects"):
        await public_fetch.fetch_public_text("https://example.com")
    assert len(requests) == public_fetch.MAX_REDIRECTS + 1


class BytesStream(httpx.AsyncByteStream):
    def __init__(self, data):
        self.data = data

    async def __aiter__(self):
        yield self.data


class Stream(httpx.AsyncByteStream):
    def __init__(self, *, slow=False):
        self.closed = False
        self.slow = slow

    async def __aiter__(self):
        for _ in range(20):
            if self.slow:
                await asyncio.sleep(.01)
            yield b"x" * 65536

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_stream_size_and_timeout_close_response(network):
    state, _, _ = network
    stream = Stream()
    state["handler"] = lambda request: httpx.Response(200, stream=stream)
    with pytest.raises(ValueError, match="response_too_large"):
        await public_fetch.fetch_public_text("https://example.com")
    assert stream.closed
    stream = Stream(slow=True)
    with pytest.raises(TimeoutError, match="deadline"):
        await public_fetch.fetch_public_text("https://example.com", deadline=time.monotonic() + .025)
    assert stream.closed


@pytest.mark.asyncio
async def test_deadline_includes_dns_and_is_shared(network, monkeypatch):
    async def slow_dns(*args, **kwargs):
        await asyncio.sleep(.1)
    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", slow_dns)
    with pytest.raises(TimeoutError, match="deadline"):
        await public_fetch.fetch_public_text("https://example.com", deadline=time.monotonic() + .01)
    assert network[1] == []
    with pytest.raises(TimeoutError, match="deadline"):
        await public_fetch.fetch_public_text("https://example.com", deadline=time.monotonic() - 1)


@pytest.mark.asyncio
@pytest.mark.parametrize("headers, error", [
    ({"content-length": "1048577"}, "response_too_large"),
    ({"content-encoding": "gzip"}, "unsupported_content_encoding"),
])
async def test_reject_oversized_header_and_compressed_body(network, headers, error):
    state, _, _ = network
    state["handler"] = lambda request: httpx.Response(200, headers=headers, stream=Stream())
    with pytest.raises(ValueError, match=error):
        await public_fetch.fetch_public_text("https://example.com")


async def invoke(tool, url):
    import json

    from agents.tool_context import ToolContext
    return await tool.on_invoke_tool(ToolContext(context=None, tool_name=tool.name, tool_call_id="test", tool_arguments=json.dumps({"url": url})), json.dumps({"url": url}))


@pytest.mark.asyncio
async def test_tools_report_errors_and_not_found_without_real_network(network):
    from opencmo.tools.ai_crawler_check import check_llms_txt
    from opencmo.tools.llmstxt import generate_llmstxt, validate_llmstxt
    for tool in (check_llms_txt, validate_llmstxt):
        result = await invoke(tool, "http://localhost")
        assert "Error" in result and "private_url" in result
    assert "Could not generate" in await invoke(generate_llmstxt, "http://localhost")
    assert network[1] == []
    network[0]["handler"] = lambda request: httpx.Response(404)
    assert "Not Found" in await invoke(check_llms_txt, "https://example.com")
    assert "No llms.txt found" in await invoke(validate_llmstxt, "https://example.com")


@pytest.mark.asyncio
async def test_tools_success_and_generation_share_deadline(network, monkeypatch):
    from opencmo.tools import llmstxt
    from opencmo.tools.ai_crawler_check import check_llms_txt
    content = "# Example\n> Description\n## Main\n- [Home](https://example.com)"
    network[0]["handler"] = lambda request: httpx.Response(200, text=content)
    assert "llms.txt Found" in await invoke(check_llms_txt, "https://example.com")
    assert "✅ Valid" in await invoke(llmstxt.validate_llmstxt, "https://example.com")
    deadlines = []
    async def fetch(url, *, deadline):
        deadlines.append(deadline)
        text = '<title>Example</title><a href="/about">About</a>'
        return httpx.Response(200, text=text)
    monkeypatch.setattr(llmstxt, "fetch_public_text", fetch)
    assert "Generated llms.txt" in await invoke(llmstxt.generate_llmstxt, "https://example.com")
    assert len(deadlines) == 3
    assert len(set(deadlines)) == 1


@pytest.mark.asyncio
async def test_missing_location_and_connection_error(network):
    state, _, _ = network
    state["handler"] = lambda request: httpx.Response(302)
    with pytest.raises(ValueError, match="invalid_redirect"):
        await public_fetch.fetch_public_text("https://example.com")

    def fail(request):
        raise httpx.ConnectError("connection failed", request=request)
    state["handler"] = fail
    from opencmo.tools.ai_crawler_check import check_llms_txt
    from opencmo.tools.llmstxt import validate_llmstxt
    for tool in (check_llms_txt, validate_llmstxt):
        assert "connection failed" in await invoke(tool, "https://example.com")


@pytest.mark.asyncio
async def test_caller_cancellation_closes_stream(network):
    stream = Stream(slow=True)
    network[0]["handler"] = lambda request: httpx.Response(200, stream=stream)
    task = asyncio.create_task(public_fetch.fetch_public_text("https://example.com"))
    await asyncio.sleep(.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert stream.closed
