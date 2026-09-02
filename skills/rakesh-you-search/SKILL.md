---
name: rakesh-you-search
description: Live web search, deep research, and page-content extraction via the You.com MCP server. Use when the user asks for a live search, wants a multi-step research synthesis, or needs the cleaned-up markdown content of a specific URL.
license: MIT
metadata:
  version: "1.0.4"
  category: mcp
  server: you-search
---

# You.com MCP

Run web searches, kick off background research, and extract the content of a specific URL through You.com's MCP server.

## Endpoint

- Authenticated (with `YDC_API_KEY` in env): `https://api.you.com/mcp` — full tool set (web search, deep research, page extraction).
- Public free profile (no key): `https://api.you.com/mcp?profile=free` — limited to 2 tools (`you-search`, `you-discover`). Verified working without any key as of 2026-09-02.
- This is the **only skill in this plugin that benefits from an API key**; the other four servers accept anonymous calls. Prefer the free profile unless the user asks for deep research or sets `YDC_API_KEY`.

## Workflow

1. Discover the current tools with `initialize` + `tools/list` over the MCP Streamable HTTP transport.
2. Pick the tool that matches the user's intent (web search, deep research, page-content extraction).
3. Build the `arguments` object strictly from the live `inputSchema` (casing and required fields matter).
4. For state-changing actions (background research tasks), confirm with the user before calling.
5. Read `result.content` and `result.structuredContent` when present. If `isError` is true, surface the server's error and the corrective action.
6. Never embed `YDC_API_KEY` in arguments or files. Read it from the environment only.

## Bundled script

The `scripts/mcp_call.py` helper runs `discover` / `call` against this endpoint and validates the tool against the live tool list before each call. Global flags (`--ttl`, `--refresh`, `--timeout`) come **before** the subcommand.

```bash
python <SKILL_DIR>/scripts/mcp_call.py discover
python <SKILL_DIR>/scripts/mcp_call.py --ttl -1 discover          # force fresh discovery
python <SKILL_DIR>/scripts/mcp_call.py call --tool you-search --args '{"query":"minimax custom plugin"}'
```

## Failure handling

- Unknown tool → re-run `tools/list` and choose from the current set.
- On the free profile, only `you-search` and `you-discover` exist. Research/extraction tools appearing missing means the free profile is active — ask the user for `YDC_API_KEY` instead of guessing tool names.
- `401` or `403` → set `YDC_API_KEY` in the environment; do not print its value.
- Schema mismatch → re-check the live `inputSchema` casing and required fields.
- Pagination cursor repeated → abort and report, do not loop.
- A transient connection drop is retried once automatically; a second failure reported as `dropped the connection twice` is a network/server issue — retry later.
