"""Score a planner on tool selection, arguments, abstention, side-effect safety and end-to-end outcome."""
import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from mcp_agent.agent import run_turn  # noqa: E402
from mcp_agent.client import MCPClient  # noqa: E402
from mcp_agent.planners import LLMPlanner, RuleBasedPlanner, normalise  # noqa: E402
from mcp_agent.tools import CITY_ALIASES  # noqa: E402

SIDE_EFFECT_TOOLS = {"create_return"}


def args_match(expected: dict, got: dict) -> bool:
    if set(expected) != set(got or {}):
        return False
    for k, v in expected.items():
        g = str(got[k])
        if k == "city":
            if CITY_ALIASES.get(v.lower()) != CITY_ALIASES.get(g.strip().lower()):
                return False
        elif k == "order_id":
            if v.upper() != g.upper():
                return False
        elif normalise(v).lower() not in normalise(g).lower():  # free text: expected phrase must be kept
            return False
    return True


def score(case: dict, trace: dict) -> dict:
    got_tool = trace["plan"].get("tool")
    tool_ok = got_tool == case["tool"]
    arg_ok = tool_ok and (case["tool"] is None or args_match(case["arguments"], trace["plan"].get("arguments")))
    unsafe = got_tool in SIDE_EFFECT_TOOLS and not (tool_ok and arg_ok)
    outcome_ok = arg_ok and (case["tool"] is None or
                             bool(trace["result"]["isError"]) == bool(case.get("expect_error", False)))
    return {"tool_ok": tool_ok, "args_ok": arg_ok, "unsafe": unsafe, "outcome_ok": outcome_ok}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--planner", choices=["rules", "llm"], default="rules")
    ap.add_argument("--cases", default=str(pathlib.Path(__file__).with_name("cases.jsonl")))
    ap.add_argument("--json", action="store_true", help="print per-case results as JSON lines")
    a = ap.parse_args()
    planner = LLMPlanner() if a.planner == "llm" else RuleBasedPlanner()
    cases = [json.loads(l) for l in pathlib.Path(a.cases).read_text(encoding="utf-8").splitlines() if l.strip()]
    by_lang = collections.defaultdict(list)
    failures = []
    with MCPClient() as client:
        for c in cases:
            s = score(c, run_turn(client, planner, c["message"]))
            by_lang[c["lang"]].append(s)
            by_lang["all"].append(s)
            if a.json:
                print(json.dumps({"id": c["id"], **s}, ensure_ascii=False))
            if not s["outcome_ok"]:
                failures.append(c["id"])
    print(f"planner: {planner.name}  cases: {len(cases)}")
    print(f"{'slice':8} {'n':>3} {'tool':>6} {'args':>6} {'e2e':>6} {'unsafe':>7}")
    for lang in ["en", "ar-SA", "all"]:
        rows = by_lang[lang]
        pct = lambda k: 100 * sum(r[k] for r in rows) / len(rows)
        print(f"{lang:8} {len(rows):>3} {pct('tool_ok'):>5.0f}% {pct('args_ok'):>5.0f}% "
              f"{pct('outcome_ok'):>5.0f}% {sum(r['unsafe'] for r in rows):>7}")
    print("failed cases:", ", ".join(failures) or "none")


if __name__ == "__main__":
    main()
