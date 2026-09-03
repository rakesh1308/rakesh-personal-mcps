# rakesh-personal-mcps

Five remote MCP servers packaged for the MiniMax Agent platform **two ways**:

1. **Native MCP** (preferred) — `.minimax-plugin/plugin.json` declares
   `rakesh-mcp.mcp.json`, which registers all five servers with the runtime.
   The runtime owns connection, reconnection, and secret injection; skills
   just teach the agent *when and how* to use each toolset.
2. **Bundled-script fallback** — each skill still ships the self-contained
   `scripts/mcp_call.py` (stdlib-only MCP Streamable HTTP client). Works even
   if the runtime ignores the plugin manifest; also usable from any shell.

## Native MCP registration (Way 2)

```
minimax-custom-plugin/
├── .minimax-plugin/
│   └── plugin.json          ← schemaVersion 1, lists mcpServers + skills
├── rakesh-mcp.mcp.json      ← the 5 MCP server configs
└── skills/
    └── rakesh-*/SKILL.md
```

- Servers on Zeabur are registered with no auth header — all four accept
  anonymous calls (verified 2026-09-02).
- `rakesh-you-search` uses `${YDC_API_KEY}` expansion; the full 6-tool set
  requires the key (free profile = 2 tools).
- Secrets are only ever `${VAR}` references — never literal values.

## Skills

| Folder | MCP server |
|---|---|
| [`skills/rakesh-adaptive-memory/`](skills/rakesh-adaptive-memory/) | Adaptive Memory — persistent memory, semantic search, knowledge graph, memory Q&A |
| [`skills/rakesh-brightdata/`](skills/rakesh-brightdata/) | Bright Data — live web search, scraping, structured extraction, browser automation |
| [`skills/rakesh-google/`](skills/rakesh-google/) | Google — Gmail, Calendar, Drive, and other Google services |
| [`skills/rakesh-screenapp/`](skills/rakesh-screenapp/) | ScreenApp — recordings, transcripts, recording Q&A |
| [`skills/rakesh-you-search/`](skills/rakesh-you-search/) | You.com — web search, deep research, page-content extraction |

## Skill structure

Every skill folder follows the standard MiniMax Agent Skills layout:

```
<skill-name>/
├── SKILL.md          ← YAML frontmatter (---) + body
├── _meta.json        ← user-supplied metadata (no id, no updated_at)
└── scripts/
    └── mcp_call.py   ← bundled CLI (stdlib-only, runs from any folder)
```

## Authentication

Only You.com actually benefits from an API key (the key unlocks the full tool
set; the free anonymous profile exposes just `you-search` and `you-discover`).
The other four Zeabur-hosted servers accept anonymous calls — tokens are
optional. If a token env var is set, it is sent as a Bearer header.

| Server | Environment variable | Required |
|---|---|---|
| Adaptive Memory | `ADAPTIVE_MEMORY_TOKEN` | No |
| Google | `GOOGLE_MCP_TOKEN` | No |
| Bright Data | `BRIGHTDATA_MCP_TOKEN` | No |
| ScreenApp | `SCREENAPP_TOKEN` (falls back to `SCREENAPP_API_TOKEN`) | No |
| You.com | `YDC_API_KEY` | No (free profile = 2 tools; key = full set) |

## Using a skill

```bash
cd skills/rakesh-brightdata
python scripts/mcp_call.py info
python scripts/mcp_call.py discover
python scripts/mcp_call.py call --tool search_engine --args '{"query":"latest minimax models"}'
```

Discovery is cached for 5 minutes per endpoint. Note that global flags
(`--ttl`, `--refresh`, `--timeout`) must come **before** the subcommand —
e.g. `python scripts/mcp_call.py --ttl -1 discover`, not `discover --ttl -1`.

## Updating

Bump the `version` field in `_meta.json` and `SKILL.md` `metadata.version`
whenever you change the skill, then push:

```bash
git add -A
git commit -m "bump version to 1.0.1"
git push
```

The MiniMax platform will pick up the new commit on its next pull.
