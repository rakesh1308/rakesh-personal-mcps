---
name: rakesh-brightdata
description: Live web search, scraping, structured data extraction, and browser automation via the Bright Data MCP server. Use when the user asks to fetch a URL, run a search engine query, extract structured data from a page, or drive a browser through a multi-step workflow.
license: MIT
metadata:
  version: "1.0.4"
  category: mcp
  server: brightdata
---

# Bright Data MCP

Reach the public web through Bright Data's MCP server: search, scrape, extract, and drive a browser.

## Endpoint

- URL: `https://brightdata-mcp-server.zeabur.app/mcp`
- Auth: **works anonymously** — no token required (verified 2026-09-02: 9 tools listed with no credentials). If `BRIGHTDATA_MCP_TOKEN` is set in the environment it is sent as a Bearer token.

## Workflow

1. Discover the current tools with `initialize` + `tools/list` over the MCP Streamable HTTP transport.
2. Pick the tool that matches the user's intent (search engine, scrape URL, structured extraction, browser navigate/click/screenshot).
3. Build the `arguments` object strictly from the live `inputSchema` (casing and required fields matter).
4. For state-changing browser actions (`browser_navigate`, scraping jobs, `browser_click`), confirm with the user before calling.
5. Read `result.content` and `result.structuredContent` when present. If `isError` is true, surface the server's error and the corrective action.
6. Never embed `BRIGHTDATA_MCP_TOKEN` in arguments or files. Read it from the environment only.

## Bundled script

The `scripts/mcp_call.py` helper runs `discover` / `call` against this endpoint and validates the tool against the live tool list before each call. Global flags (`--ttl`, `--refresh`, `--timeout`) come **before** the subcommand.

```bash
python <SKILL_DIR>/scripts/mcp_call.py discover
python <SKILL_DIR>/scripts/mcp_call.py --ttl -1 discover          # force fresh discovery
python <SKILL_DIR>/scripts/mcp_call.py call --tool search_engine --args '{"query":"latest minimax models"}'
```

## Failure handling

- Unknown tool → re-run `tools/list` and choose from the current set.
- `401` or `403` → the server rejected the anonymous/guest identity for this action; if `BRIGHTDATA_MCP_TOKEN` is available, set it in the environment and retry. Do not print its value.
- Schema mismatch → re-check the live `inputSchema` casing and required fields.
- Pagination cursor repeated → abort and report, do not loop.
- A transient connection drop is retried once automatically; a second failure reported as `dropped the connection twice` is a network/server issue — retry later.
