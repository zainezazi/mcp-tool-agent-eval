"""A minimal Model Context Protocol server over stdio (JSON-RPC 2.0, one message per line).

Implements initialize, tools/list and tools/call, which is enough for MCP clients
to discover and call the tools in tools.py. No third-party dependencies.
"""
import json
import sys

from .tools import TOOLS, ToolError

PROTOCOL_VERSION = "2025-06-18"


def _validate(schema: dict, args: dict) -> None:
    if not isinstance(args, dict):
        raise ToolError("arguments must be an object")
    missing = [k for k in schema.get("required", []) if k not in args]
    if missing:
        raise ToolError(f"missing required arguments: {missing}")
    extra = [k for k in args if k not in schema.get("properties", {})]
    if extra:
        raise ToolError(f"unexpected arguments: {extra}")


def handle(msg: dict):
    method, mid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if mid is None:  # notification (e.g. notifications/initialized): no reply
        return None
    if method == "initialize":
        result = {"protocolVersion": PROTOCOL_VERSION,
                  "capabilities": {"tools": {"listChanged": False}},
                  "serverInfo": {"name": "nakheel-store-demo", "version": "0.1.0"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{"name": n, "description": t["description"], "inputSchema": t["inputSchema"]}
                            for n, t in TOOLS.items()]}
    elif method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in TOOLS:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"unknown tool {name}"}}
        try:
            _validate(TOOLS[name]["inputSchema"], args)
            out = TOOLS[name]["fn"](**args)
            result = {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}],
                      "structuredContent": out, "isError": False}
        except ToolError as e:  # tool errors are reported to the model, not as protocol errors
            result = {"content": [{"type": "text", "text": str(e)}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            reply = handle(json.loads(line))
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
