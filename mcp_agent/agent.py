"""One-turn agent: discover tools over MCP, let a planner pick one, call it, and answer."""
import argparse
import json

from .client import MCPClient
from .planners import LLMPlanner, RuleBasedPlanner


def run_turn(client: MCPClient, planner, message: str) -> dict:
    tools = client.list_tools()
    plan = planner.plan(message, tools)
    trace = {"message": message, "plan": plan, "result": None}
    if plan.get("tool"):
        trace["result"] = client.call_tool(plan["tool"], plan["arguments"])
    return trace


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("message")
    ap.add_argument("--planner", choices=["rules", "llm"], default="rules")
    a = ap.parse_args()
    planner = LLMPlanner() if a.planner == "llm" else RuleBasedPlanner()
    with MCPClient() as c:
        print(json.dumps(run_turn(c, planner, a.message), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
