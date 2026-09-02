---
name: rakesh-adaptive-memory
description: Persistent memory, semantic search, knowledge graph, and memory Q&A via the Adaptive Memory MCP server. Use when the user asks to recall past notes, store a new memory, query long-term knowledge, or traverse relationships between stored items.
license: MIT
metadata:
  version: "1.0.0"
  category: mcp
  server: adaptive-memory
---

# Adaptive Memory MCP

Reach persistent memory, semantic recall, and a knowledge graph through the Adaptive Memory MCP server.

## Endpoint

- URL: `https://adaptivememory.zeabur.app/mcp`
- Auth: Bearer token from the `ADAPTIVE_MEMORY_TOKEN` environment variable.

## Workflow

1. Discover the current tools with `initialize` + `tools/list` over the MCP Streamable HTTP transport.
2. Pick the tool that matches the user's intent (memory read/write, semantic search, knowledge-graph traversal, memory Q&A).
3. Build the `arguments` object strictly from the live `inputSchema` (casing and required fields matter).
4. For state-changing actions (create, update, delete, import, restore), confirm with the user before calling.
5. Read `result.content` and `result.structuredContent` when present. If `isError` is true, surface the server's error and the corrective action.
6. Never embed `ADAPTIVE_MEMORY_TOKEN` in arguments or files. Read it from the environment only.

## Bundled script

The `scripts/mcp_call.py` helper runs `discover` / `call` against this endpoint and validates the tool against the live tool list before each call. Use it when you need a quick CLI check; the agent itself can also call the MCP endpoint directly.

```bash
python <SKILL_DIR>/scripts/mcp_call.py discover
python <SKILL_DIR>/scripts/mcp_call.py call --tool get_stats --args '{}'
```

## Failure handling

- Unknown tool → re-run `tools/list` and choose from the current set.
- `401` or `403` → set `ADAPTIVE_MEMORY_TOKEN` in the environment; do not print its value.
- Schema mismatch → re-check the live `inputSchema` casing and required fields.
- Pagination cursor repeated → abort and report, do not loop.
