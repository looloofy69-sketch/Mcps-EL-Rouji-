# EL-Rouji MCP Adapter

A local Model Context Protocol (MCP) server that connects MCP-compatible clients to the existing EL-Rouji application API. It is an adapter, not a replacement backend.

## Implemented tools

| Tool | Purpose | Default |
|---|---|---|
| `el_rouji_health` | Read the configured application's `/api/health` endpoint | Enabled |
| `el_rouji_chat` | Send one bounded prompt to `/api/chat` | Disabled |
| `el_rouji_research` | Send a bounded search query to `/api/research` | Disabled |
| `el_rouji_analyze_text` | Submit supplied text for TXT, MD, CSV, or JSON analysis | Disabled |

The adapter does not read arbitrary local files, accept user-provided upstream URLs, store conversations, implement scheduled jobs, connect commerce/payment flows, or execute arbitrary tools. Direct URL scraping is deliberately not exposed through the MCP research tool.

## Requirements and local run

Python 3.11 or later is required. Install the package in a virtual environment:

```sh
python -m venv .venv
# Linux/macOS:
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
el-rouji-mcp
```

The server uses MCP over stdio by default, so an MCP host starts it as a local subprocess. Do not print diagnostics to stdout; stdout is used by the protocol.

## Configuration

- `EL_ROUJI_BASE_URL`: origin of the existing EL-Rouji deployment. Defaults to `https://el-rouji-70120b.v2.appdeploy.ai`. Only an HTTP(S) origin is allowed; remote services must use HTTPS.
- `EL_ROUJI_ENABLE_GENERATION`: defaults to disabled. Set to `true` only when you knowingly accept that tool calls invoke the hosted application's AI/search endpoints and their usage costs. This is a local opt-in, not a substitute for server-side authentication, rate limiting, or quotas.
- `LOG_LEVEL`: optional logging level; defaults to `WARNING`. Logs go to stderr.

Example MCP host configuration (replace the path with the absolute path on your own machine):

```json
{
  "mcpServers": {
    "el-rouji": {
      "command": "/absolute/path/to/repository/.venv/bin/el-rouji-mcp",
      "env": {
        "EL_ROUJI_BASE_URL": "https://el-rouji-70120b.v2.appdeploy.ai",
        "EL_ROUJI_ENABLE_GENERATION": "false"
      }
    }
  }
}
```

## Security and reliability

- Generation tools are disabled unless explicitly enabled in the local MCP process environment.
- HTTP redirects are not followed; API routes are fixed constants rather than tool-supplied URLs.
- Base URLs containing credentials, paths, query strings, or fragments are rejected. Plain HTTP is allowed only for localhost development.
- Prompt, document, and response sizes are bounded.
- The adapter does not claim to add server-side rate limiting, account identity, authorization, or quotas to the existing API. Review those controls before broad or shared deployment.
- Do not configure this server for untrusted MCP clients. Do not embed secrets in prompts, tool arguments, repository files, or host configuration committed to source control.

## Source of truth

The application implementation and API contracts live in [EL-Rouji core](https://github.com/looloofy69-sketch/EL-Rouji). Current platform and integration limits are documented in the [core integration notes](https://github.com/looloofy69-sketch/EL-Rouji/blob/main/docs/INTEGRATIONS.md).

The automated tests cover configuration, fixed API-path enforcement, response bounds, redirect behavior, error handling, generation opt-in, URL-scrape rejection, and filename boundaries. They do not prove authorization or live connectivity. A manually invoked [Live read-only health smoke workflow](.github/workflows/live-health-smoke.yml) calls the registered health-tool handler against the configured deployment with generation disabled. It does not validate MCP stdio negotiation, and it does not call chat/research or prove those routes' authorization or cost controls. Live generation testing must remain separate and explicitly controlled.
