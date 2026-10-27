"""MCP tools that safely call the existing EL-Rouji HTTP API."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Literal, Any

import httpx
from mcp.server import MCPServer

from .config import (
    generation_enabled,
    normalize_base_url,
    validate_language,
    validate_mode,
    validate_text,
)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "WARNING").upper())
logger = logging.getLogger("el_rouji_mcp")
BASE_URL = normalize_base_url()
MAX_RESPONSE_BYTES = 1_000_000
mcp = MCPServer("EL-Rouji MCP")


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _require_generation_enabled() -> None:
    if not generation_enabled():
        raise ValueError(
            "Generation tools are disabled by default. Set EL_ROUJI_ENABLE_GENERATION=true "
            "after reviewing endpoint usage, cost, and rate-limit controls."
        )


async def _request_json(method: Literal["GET", "POST"], path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    # Paths are internal constants; no tool accepts a URL or arbitrary endpoint.
    if not path.startswith("/api/") or "://" in path or ".." in path:
        raise ValueError("Invalid internal API path.")
    timeout = httpx.Timeout(45.0, connect=5.0)
    chunks: list[bytes] = []
    size = 0
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        async with client.stream(
            method,
            f"{BASE_URL}{path}",
            json=payload,
            headers={"Accept": "application/json"},
        ) as response:
            # Stream and count decoded bytes before retaining the full body. A
            # post-read len(response.content) check would still buffer an
            # oversized response in memory before rejecting it.
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > MAX_RESPONSE_BYTES:
                    raise RuntimeError("EL-Rouji returned a response larger than the adapter limit.")
                chunks.append(chunk)
            status_code = response.status_code

    if status_code < 200 or status_code >= 300:
        logger.warning("EL-Rouji API request failed: path=%s status=%s", path, status_code)
        raise RuntimeError(f"EL-Rouji API returned HTTP {status_code}.")
    try:
        data = json.loads(b"".join(chunks))
    except ValueError as exc:
        raise RuntimeError("EL-Rouji returned a non-JSON response.") from exc
    if not isinstance(data, dict):
        raise RuntimeError("EL-Rouji returned an unexpected response shape.")
    return data


@mcp.tool()
async def el_rouji_health() -> str:
    """Check the configured EL-Rouji application health endpoint (read-only)."""
    try:
        data = await _request_json("GET", "/api/health")
        return _json_text({"reachable": True, "baseUrl": BASE_URL, "health": data})
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        logger.warning("EL-Rouji health check failed: %s", type(exc).__name__)
        return _json_text({"reachable": False, "baseUrl": BASE_URL, "error": str(exc)})


@mcp.tool()
async def el_rouji_chat(
    prompt: str,
    language: Literal["en", "fr", "ar"] = "en",
    mode: Literal["assistant", "research", "writing", "study", "coding", "planning"] = "assistant",
) -> str:
    """Send one bounded prompt to EL-Rouji. Disabled unless generation is explicitly enabled locally."""
    _require_generation_enabled()
    prompt = validate_text(prompt, "prompt", 6000)
    language = validate_language(language)
    mode = validate_mode(mode)
    data = await _request_json("POST", "/api/chat", {
        "messages": [{"role": "user", "content": prompt}],
        "language": language,
        "mode": mode,
    })
    reply = data.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        raise RuntimeError("EL-Rouji did not return a usable chat reply.")
    return _json_text({"assistant": data.get("assistant", "EL-Rouji"), "reply": reply})


@mcp.tool()
async def el_rouji_research(
    query: str,
    language: Literal["en", "fr", "ar"] = "en",
) -> str:
    """Run a bounded web-search research query. Direct URL scraping is intentionally not exposed."""
    _require_generation_enabled()
    query = validate_text(query, "query", 400)
    if query.lower().startswith(("http://", "https://")):
        raise ValueError("Pass a research question, not a URL. Direct URL scraping is not exposed through this MCP adapter.")
    language = validate_language(language)
    data = await _request_json("POST", "/api/research", {"query": query, "language": language})
    reply = data.get("reply")
    sources = data.get("sources", [])
    if not isinstance(reply, str) or not isinstance(sources, list):
        raise RuntimeError("EL-Rouji returned an unexpected research response.")
    return _json_text({"reply": reply, "sources": sources})


@mcp.tool()
async def el_rouji_analyze_text(
    filename: str,
    content: str,
    question: str = "",
    language: Literal["en", "fr", "ar"] = "en",
) -> str:
    """Analyze explicitly supplied TXT, MD, CSV, or JSON text; does not read local files."""
    _require_generation_enabled()
    filename = validate_text(filename, "filename", 180)
    if Path(filename).name != filename or Path(filename).suffix.lower() not in {".txt", ".md", ".csv", ".json"}:
        raise ValueError("filename must be a simple filename ending in .txt, .md, .csv, or .json.")
    content = validate_text(content, "content", 100_000)
    question = validate_text(question, "question", 4000, allow_empty=True)
    language = validate_language(language)
    data = await _request_json("POST", "/api/analyze-document", {
        "filename": filename,
        "content": content,
        "question": question,
        "language": language,
    })
    reply = data.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        raise RuntimeError("EL-Rouji did not return a usable document analysis.")
    return _json_text({"reply": reply, "analyzed": bool(data.get("analyzed", True))})


def main() -> None:
    """Run as a local MCP stdio process."""
    mcp.run()


if __name__ == "__main__":
    main()
