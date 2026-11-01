import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from mcp_agent.client import MCPClient  # noqa: E402
from mcp_agent.planners import RuleBasedPlanner  # noqa: E402
from mcp_agent.server import handle  # noqa: E402


class ServerTests(unittest.TestCase):
    def test_initialize_and_list(self):
        r = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertIn("tools", r["result"]["capabilities"])
        names = [t["name"] for t in handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]]
        self.assertEqual(sorted(names), ["create_return", "list_branches", "track_order"])

    def test_notification_gets_no_reply(self):
        self.assertIsNone(handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_schema_validation_is_tool_error(self):
        r = handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                    "params": {"name": "create_return", "arguments": {"order_id": "NK-1002"}}})
        self.assertTrue(r["result"]["isError"])

    def test_unknown_method(self):
        self.assertEqual(handle({"jsonrpc": "2.0", "id": 4, "method": "nope"})["error"]["code"], -32601)


class EndToEndTests(unittest.TestCase):
    def test_stdio_round_trip(self):
        with MCPClient() as c:
            out = c.call_tool("list_branches", {"city": "جدة"})
            self.assertFalse(out["isError"])
            self.assertEqual(len(json.loads(out["content"][0]["text"])["branches"]), 2)

    def test_return_needs_reason(self):
        plan = RuleBasedPlanner().plan("ابغى ارجع NK-1002", [])
        self.assertIsNone(plan["tool"])


if __name__ == "__main__":
    unittest.main()
