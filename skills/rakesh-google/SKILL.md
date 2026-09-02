---
name: rakesh-google
description: Read and modify Gmail, Google Calendar, Google Drive, and other Google services exposed by the remote Google MCP server. Use when the user asks to send or read email, list or create calendar events, upload or fetch Drive files, or query another Google API endpoint the server exposes.
license: MIT
metadata:
  version: "1.0.0"
  category: mcp
  server: google
---

# Google MCP

Reach Gmail, Calendar, Drive, and other Google services through the Google MCP server.

## Endpoint

- URL: `https://google-mcp.zeabur.app/mcp`
- Auth: Bearer token from the `GOOGLE_MCP_TOKEN` environment variable.

## Workflow

1. Discover the current tools with `initialize` + `tools/list` over the MCP Streamable HTTP transport.
2. Pick the tool that matches the user's intent (Gmail send/read, Calendar list/create, Drive upload/fetch).
3. Build the `arguments` object strictly from the live `inputSchema` (casing and required fields matter).
4. For state-changing actions (send, delete, create, update), confirm with the user before calling.
5. Read `result.content` and `result.structuredContent` when present. If `isError` is true, surface the server's error and the corrective action.
6. Never embed `GOOGLE_MCP_TOKEN` in arguments or files. Read it from the environment only.

## Bundled script

The `scripts/mcp_call.py` helper runs `discover` / `call` against this endpoint and validates the tool against the live tool list before each call.

```bash
python <SKILL_DIR>/scripts/mcp_call.py discover
python <SKILL_DIR>/scripts/mcp_call.py call --tool list_events --args '{"calendarId":"primary","maxResults":10}'
```

## Failure handling

- Unknown tool → re-run `tools/list` and choose from the current set.
- `401` or `403` → set `GOOGLE_MCP_TOKEN` in the environment; do not print its value.
- Schema mismatch → re-check the live `inputSchema` casing and required fields.
- Pagination cursor repeated → abort and report, do not loop.
