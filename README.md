# EL-Rouji MCP Adapter

Local Model Context Protocol (MCP) server for connecting MCP-compatible clients to the existing EL-Rouji application API.

**Initial status:** repository bootstrapping. The README is the seed commit; executable server code is added in the implementation pull request.

## Scope and trust boundary

This repository is an adapter, not a replacement for the EL-Rouji frontend/backend. It must call only the configured EL-Rouji base URL, must not accept arbitrary upstream URLs from tool arguments, and must not persist conversation data by default.

The current EL-Rouji backend exposes public chat and research routes. Because generation can consume provider resources, generation tools must be disabled by default and require an explicit local opt-in. The health tool is read-only. Enable generation only after reviewing endpoint usage and cost/rate-limit controls.

## Target tools

- `el_rouji_health` — read the configured application's health endpoint.
- `el_rouji_chat` — forward one prompt to the existing chat endpoint when generation is explicitly enabled.
- `el_rouji_research` — forward a bounded query to the existing research endpoint when enabled; direct URL scraping is not exposed through this MCP tool.
- `el_rouji_analyze_text` — forward explicitly supplied text in a supported file format when enabled. The adapter does not read arbitrary local files.

The adapter does not implement scheduled jobs, commerce, dataset ingestion, account synchronization, or tool execution outside the documented EL-Rouji API.

See [EL-Rouji core](https://github.com/looloofy69-sketch/EL-Rouji) for the source application and [its integration notes](https://github.com/looloofy69-sketch/EL-Rouji/blob/main/docs/INTEGRATIONS.md) for current service boundaries.
