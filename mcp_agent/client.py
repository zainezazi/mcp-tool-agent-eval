"""Minimal stdio MCP client: spawns the server as a subprocess and talks JSON-RPC to it."""
import itertools
import json
import subprocess
import sys


class MCPClient:
    def __init__(self, cmd=None):
        self.proc = subprocess.Popen(cmd or [sys.executable, "-m", "mcp_agent.server"],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     text=True, encoding="utf-8")
        self._ids = itertools.count(1)
        self.server_info = self.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                                       "clientInfo": {"name": "demo-client", "version": "0.1.0"}})
        self.notify("notifications/initialized")

    def notify(self, method, params=None):
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method, "params": params or {}}) + "\n")
        self.proc.stdin.flush()

    def request(self, method, params=None):
        mid = next(self._ids)
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": mid, "method": method,
                                          "params": params or {}}, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()
        reply = json.loads(self.proc.stdout.readline())
        if "error" in reply:
            raise RuntimeError(reply["error"]["message"])
        return reply["result"]

    def list_tools(self):
        return self.request("tools/list")["tools"]

    def call_tool(self, name, arguments):
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=5)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
