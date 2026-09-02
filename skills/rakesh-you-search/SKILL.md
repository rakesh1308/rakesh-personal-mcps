---
name: rakesh-you-search
description: Live web search, deep research, and page-content extraction via the You.com MCP server. Use when the user asks for a live search, wants a multi-step research synthesis, or needs the cleaned-up markdown content of a specific URL.
license: MIT
metadata:
  version: "1.0.2"
  category: mcp
  server: you-search
---

# You.com MCP

Run web searches, kick off background research, and extract the content of a specific URL through You.com's MCP server.

## Endpoint

- Authenticated URL (when `YDC_API_KEY` is set): `https://api.you.com/mcp`
- Public URL (otherwise): `https://api.you.com/mcp?profile=free`
- Auth: Bearer token from the `YDC_API_KEY` environment variable. Without it the public free endpoint is used.

## Workflow

1. Discover the current tools with `initialize` + `tools/list` over the MCP Streamable HTTP transport.
2. Pick the tool that matches the user's intent (web search, deep research, page-content extraction).
3. Build the `arguments` object strictly from the live `inputSchema` (casing and required fields matter).
4. For state-changing actions (background research tasks), confirm with the user before calling.
5. Read `result.content` and `result.structuredContent` when present. If `isError` is true, surface the server's error and the corrective action.
6. Never embed `YDC_API_KEY` in arguments or files. Read it from the environment only.

## Bundled script

The `scripts/mcp_call.py` helper runs `discover` / `call` against this endpoint and validates the tool against the live tool list before each call.

```bash
python <SKILL_DIR>/scripts/mcp_call.py discover
python <SKILL_DIR>/scripts/mcp_call.py call --tool you-search --args '{"query":"minimax custom plugin"}'
```

## Failure handling

- Unknown tool → re-run `tools/list` and choose from the current set.
- `401` or `403` → set `YDC_API_KEY` in the environment; do not print its value.
- Schema mismatch → re-check the live `inputSchema` casing and required fields.
- Pagination cursor repeated → abort and report, do not loop.
