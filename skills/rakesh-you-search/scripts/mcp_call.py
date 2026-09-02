"""Standalone You.com MCP client.

Self-contained: transport + cache are inlined so the script has no external
imports beyond the Python standard library. Run from this skill's scripts/
folder or any path that can see the bundled modules.

Usage:
    python scripts/mcp_call.py discover
    python scripts/mcp_call.py info
    python scripts/mcp_call.py call --tool TOOL --args '{"key":"value"}'
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
import uuid
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse


# Inlined MCP Streamable HTTP transport (self-contained).
PROTOCOL_VERSION = "2024-11-05"
CLIENT_NAME = "rakesh-you-search-skill"
CLIENT_VERSION = "1.2.0"


class McpError(RuntimeError):
    """An actionable MCP transport or protocol failure."""


class HttpMcpClient:
    def __init__(self, endpoint, token=None, timeout=60.0, allow_insecure_http=False):
        self.endpoint = endpoint.strip()
        self.token = token.strip() if token else None
        self.timeout = timeout
        self.session_id = None
        self.server_info = {}
        self._initialized = False
        self._validate_endpoint(allow_insecure_http)

    def _validate_endpoint(self, allow_insecure_http):
        parsed = urlparse(self.endpoint)
        if parsed.scheme == "https" and parsed.netloc:
            return
        if allow_insecure_http and parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1"):
            return
        raise McpError("Endpoint must use HTTPS (HTTP only allowed for localhost with --allow-http).")

    def _headers(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": f"{CLIENT_NAME}/{CLIENT_VERSION}",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, payload):
        request_id = payload.get("id")
        req = urlrequest.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=self.timeout) as response:
                sid = response.headers.get("Mcp-Session-Id")
                if sid:
                    self.session_id = sid
                raw = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise McpError(f"HTTP {exc.code} from {self.endpoint}: {raw.strip()[:500]}") from exc
        except URLError as exc:
            raise McpError(f"Could not connect to {self.endpoint}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise McpError(f"Timed out connecting to {self.endpoint} after {{self.timeout:g}}s") from exc
        if not raw.strip():
            return {}
        return _last_message(raw, request_id)

    def _rpc(self, method, params=None):
        payload = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method}
        if params is not None:
            payload["params"] = params
        envelope = self._request(payload)
        if "error" in envelope:
            raise McpError(f"{method} failed: {envelope['error'].get('message', envelope['error'])}")
        result = envelope.get("result", {})
        return result if isinstance(result, dict) else {"value": result}

    def initialize(self):
        if self._initialized:
            return self.server_info
        result = self._rpc("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
        })
        self.server_info = result.get("serverInfo", {})
        self._request({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self._initialized = True
        return result

    def list_tools(self):
        self.initialize()
        tools = []
        cursor = None
        seen = set()
        while True:
            params = {"cursor": cursor} if cursor else {}
            result = self._rpc("tools/list", params)
            page = result.get("tools", [])
            if not isinstance(page, list):
                raise McpError("tools/list returned an invalid tools value.")
            tools.extend(t for t in page if isinstance(t, dict))
            cursor = result.get("nextCursor")
            if not cursor:
                return tools
            if cursor in seen:
                raise McpError("tools/list returned a repeated pagination cursor.")
            seen.add(cursor)

    def call_tool(self, name, arguments=None):
        self.initialize()
        return self._rpc("tools/call", {"name": name, "arguments": arguments or {}})


def _last_message(raw, request_id):
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            return value if request_id is None or value.get("id") == request_id else value
    except json.JSONDecodeError:
        pass
    messages = []
    data_lines = []
    for line in raw.splitlines() + [""]:
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
        elif not line.strip() and data_lines:
            joined = "\n".join(data_lines)
            data_lines = []
            try:
                value = json.loads(joined)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                messages.append(value)
    if not messages:
        raise McpError("Server returned neither JSON nor a valid SSE JSON-RPC message.")
    if request_id is not None:
        for message in messages:
            if message.get("id") == request_id:
                return message
    return messages[-1]


# Inlined short-lived tool-list cache (self-contained).
DEFAULT_TTL = 300.0
_CACHE = {}


def _cache_path():
    override = os.environ.get("MCP_CACHE_FILE")
    if override:
        return pathlib.Path(override)
    base = os.environ.get("XDG_CACHE_HOME") or os.environ.get("LOCALAPPDATA") or str(pathlib.Path.home())
    path = pathlib.Path(base) / "minimax-mcp" / "tools-cache.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        return None


def _auth_fingerprint(client):
    return "authed" if client.token else "anon"


def _disk_load():
    path = _cache_path()
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _disk_store(payload):
    path = _cache_path()
    if not path:
        return
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def get_tools(client, *, ttl=DEFAULT_TTL, refresh=False):
    key = (client.endpoint, _auth_fingerprint(client))
    now = time.time()
    meta = {"source": "network", "ttl": ttl, "endpoint": client.endpoint}
    if ttl < 0:
        tools = client.list_tools()
        meta["age"] = 0
        return tools, meta
    if not refresh:
        cached = _CACHE.get(key)
        if cached and now - cached[0] < ttl:
            meta.update({"source": "memory", "age": now - cached[0]})
            return cached[1], meta
        disk = _disk_load()
        entry = disk.get(key)
        if entry and now - entry[0] < ttl:
            tools = entry[1]
            _CACHE[key] = (entry[0], tools)
            meta.update({"source": "disk", "age": now - entry[0]})
            return tools, meta
    tools = client.list_tools()
    _CACHE[key] = (now, tools)
    disk = _disk_load()
    disk[key] = [now, tools]
    _disk_store(disk)
    meta["age"] = 0
    return tools, meta


def invalidate(endpoint=None):
    removed = 0
    if endpoint is None:
        removed = len(_CACHE)
        _CACHE.clear()
        path = _cache_path()
        if path and path.exists():
            try:
                path.unlink()
            except OSError:
                pass
        return removed
    for key in [k for k in _CACHE if k[0] == endpoint]:
        _CACHE.pop(key, None)
        removed += 1
    disk = _disk_load()
    disk.pop((endpoint, "anon"), None)
    disk.pop((endpoint, "authed"), None)
    _disk_store(disk)
    return removed


ALIAS = 'you_search'
ENDPOINT = 'https://api.you.com/mcp?profile=free'
PRIMARY_TOKEN_ENV = 'YDC_API_KEY'



def _token():
    value = os.environ.get(PRIMARY_TOKEN_ENV) or ""
    return value or None


def _build_parser():
    parser = argparse.ArgumentParser(description="You.com MCP client (you_search)")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--allow-http", action="store_true")
    parser.add_argument("--ttl", type=float, default=DEFAULT_TTL)
    parser.add_argument("--refresh", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    discover = sub.add_parser("discover", help="Fetch live tool list (cached)")
    discover.add_argument("--query")

    sub.add_parser("info")

    purge = sub.add_parser("invalidate-cache", help="Drop cached tool list")
    purge.add_argument("--all", action="store_true")

    call = sub.add_parser("call", help="Validate then call a live tool")
    call.add_argument("--tool", required=True)
    call.add_argument("--args")
    call.add_argument("--args-file")
    return parser


def _parse_args(raw, file_path):
    if raw and file_path:
        raise McpError("Use either --args or --args-file, not both.")
    try:
        value = json.loads(pathlib.Path(file_path).read_text(encoding="utf-8")) if file_path else json.loads(raw or "{}")
    except (OSError, json.JSONDecodeError) as exc:
        raise McpError(f"Tool arguments are not a readable JSON object: {exc}") from exc
    if not isinstance(value, dict):
        raise McpError("Tool arguments must be a JSON object.")
    return value


def main():
    args = _build_parser().parse_args()
    try:
        if args.command == "info":
            info = {
                "alias": ALIAS,
                "endpoint": ENDPOINT,
                "token_env": PRIMARY_TOKEN_ENV,
                "token_configured": bool(_token()),
                "cache_ttl": args.ttl,
            }
            print(json.dumps(info, indent=2))
            return 0
        if args.command == "invalidate-cache":
            removed = invalidate(None if args.all else ENDPOINT)
            print(json.dumps({"ok": True, "removed": removed}, indent=2))
            return 0
        client = HttpMcpClient(
            ENDPOINT,
            token=_token(),
            timeout=args.timeout,
            allow_insecure_http=args.allow_http,
        )
        if args.command == "discover":
            tools, meta = get_tools(client, ttl=args.ttl, refresh=args.refresh)
            query = (args.query or "").casefold()
            if query:
                tools = [t for t in tools if query in f"{t.get('name', '')} {t.get('description', '')}".casefold()]
            print(json.dumps({
                "ok": True,
                "server": ALIAS,
                "endpoint": ENDPOINT,
                "tool_count": len(tools),
                "cache": meta,
                "tools": tools,
            }, ensure_ascii=False, indent=2))
            return 0
        if args.command == "call":
            tools, meta = get_tools(client, ttl=args.ttl, refresh=args.refresh)
            if not any(t.get("name") == args.tool for t in tools):
                names = [t.get("name") for t in tools if t.get("name")]
                raise McpError(f"Tool '{args.tool}' is not currently exposed. Current tools: {', '.join(names)}")
            tool_args = _parse_args(args.args, args.args_file)
            result = client.call_tool(args.tool, tool_args)
            print(json.dumps({
                "ok": not bool(result.get("isError")),
                "server": ALIAS,
                "endpoint": ENDPOINT,
                "tool": args.tool,
                "arguments": tool_args,
                "cache": meta,
                "result": result,
            }, ensure_ascii=False, indent=2))
            return 0
    except McpError as exc:
        print(json.dumps({"ok": False, "server": ALIAS, "error": str(exc)}, indent=2))
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
