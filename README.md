# rakesh-personal-mcps

Five self-contained MCP (Model Context Protocol) skills for the MiniMax Agent
platform. Each skill lives in its own folder so you can register them
individually or all at once.

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
