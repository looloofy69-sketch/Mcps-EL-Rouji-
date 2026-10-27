import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

from el_rouji_mcp import server


class FakeResponse:
    def __init__(self, *, status_code=200, content=b'{"ok": true}'):
        self.status_code = status_code
        self.content = content
        self.chunks_yielded = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def aiter_bytes(self, chunk_size=65_536):
        for start in range(0, len(self.content), chunk_size):
            self.chunks_yielded += 1
            yield self.content[start:start + chunk_size]


class FakeAsyncClient:
    def __init__(self, response):
        self.response = response
        self.request_args = None
        self.follow_redirects = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def stream(self, method, url, *, json=None, headers=None):
        self.request_args = {
            "method": method,
            "url": url,
            "json": json,
            "headers": headers,
        }
        return self.response


class RequestJsonTests(unittest.TestCase):
    def call(self, response, method="GET", path="/api/health", payload=None):
        client = FakeAsyncClient(response)
        with patch.object(server.httpx, "AsyncClient", return_value=client) as client_factory:
            result = asyncio.run(server._request_json(method, path, payload))
        self.assertFalse(client_factory.call_args.kwargs["follow_redirects"])
        return result, client

    def test_success_uses_configured_origin_and_fixed_api_path(self):
        with patch.object(server, "BASE_URL", "https://example.test"):
            data, client = self.call(FakeResponse(content=b'{"ok":true}'))
        self.assertEqual(data, {"ok": True})
        self.assertEqual(client.request_args["url"], "https://example.test/api/health")
        self.assertEqual(client.request_args["headers"], {"Accept": "application/json"})

    def test_arbitrary_or_traversal_paths_are_rejected_before_network_call(self):
        for path in ("https://example.test/api/chat", "/api/../admin", "/elsewhere"):
            with self.subTest(path=path):
                with patch.object(server.httpx, "AsyncClient") as client_factory:
                    with self.assertRaises(ValueError):
                        asyncio.run(server._request_json("GET", path))
                    client_factory.assert_not_called()

    def test_non_success_status_is_rejected_without_echoing_response_body(self):
        response = FakeResponse(status_code=503, content=b"provider secret body")
        with self.assertRaisesRegex(RuntimeError, "HTTP 503"):
            self.call(response)

    def test_oversized_response_stops_streaming_before_full_body_is_buffered(self):
        response = FakeResponse(content=b"x" * (server.MAX_RESPONSE_BYTES * 2))
        with self.assertRaisesRegex(RuntimeError, "larger than the adapter limit"):
            self.call(response)
        total_chunks = (len(response.content) + 65_535) // 65_536
        self.assertLess(response.chunks_yielded, total_chunks)

    def test_invalid_json_and_non_object_json_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "non-JSON response"):
            self.call(FakeResponse(content=b"not-json"))
        with self.assertRaisesRegex(RuntimeError, "unexpected response shape"):
            self.call(FakeResponse(content=b"[1,2,3]"))


class ToolBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_tool_reports_reachable_for_valid_health_response(self):
        with patch.object(server, "_request_json", new=AsyncMock(return_value={
            "ok": True, "name": "EL-Rouji", "service": "core-assistant"
        })):
            result = json.loads(await server.el_rouji_health())
        self.assertTrue(result["reachable"])
        self.assertTrue(result["health"]["ok"])

    async def test_generation_tools_are_disabled_without_explicit_opt_in(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "disabled by default"):
                await server.el_rouji_chat("test prompt")

    async def test_research_tool_does_not_forward_direct_urls(self):
        with patch.dict("os.environ", {"EL_ROUJI_ENABLE_GENERATION": "true"}, clear=True):
            with patch.object(server, "_request_json", new=AsyncMock()) as request:
                with self.assertRaisesRegex(ValueError, "not a URL"):
                    await server.el_rouji_research("https://example.com")
                request.assert_not_awaited()

    async def test_text_tool_rejects_path_traversal_and_unsupported_files(self):
        with patch.dict("os.environ", {"EL_ROUJI_ENABLE_GENERATION": "true"}, clear=True):
            with self.assertRaisesRegex(ValueError, "simple filename"):
                await server.el_rouji_analyze_text("../secret.txt", "content")
            with self.assertRaisesRegex(ValueError, "simple filename"):
                await server.el_rouji_analyze_text("file.exe", "content")


if __name__ == "__main__":
    unittest.main()
