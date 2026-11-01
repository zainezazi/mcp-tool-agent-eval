# mcp-tool-agent-eval

A small, dependency-free **Model Context Protocol (MCP) tool server**, a stdio client, a one-turn agent loop, and an **evaluation harness for tool calling** in English and Saudi-dialect Arabic.

> Portfolio demo. "Nakheel Store" is a fictional retailer; every order, branch and test message was written for this repo. It is not production code and has not been used in production.

## Why

When an LLM agent can call tools, the interesting failures aren't wrong sentences, they're wrong actions: calling the wrong tool, inventing an argument, or triggering a side effect (here, opening a return) when it should have asked a question. This repo makes those failures measurable.

## What's inside

| Path | What it does |
| --- | --- |
| `mcp_agent/server.py` | MCP server over stdio (JSON-RPC 2.0): `initialize`, `ping`, `tools/list`, `tools/call`, with input-schema checks. Tool failures come back as `isError` results the model can read, not protocol errors. |
| `mcp_agent/tools.py` | Three tools on synthetic data: `track_order`, `list_branches` (Arabic or English city names) and `create_return` (side effect, 14-day window, needs a reason). |
| `mcp_agent/client.py` | Minimal MCP client that spawns the server and does the handshake. |
| `mcp_agent/planners.py` | `RuleBasedPlanner`, an offline baseline that handles Arabic-Indic digits and Saudi-dialect phrasing, and `LLMPlanner`, an optional adapter for any OpenAI-compatible tool-calling endpoint. |
| `eval/cases.jsonl` | 24 labelled cases (13 English, 11 Saudi dialect), including ones where the right move is to ask, not act. |
| `eval/run_eval.py` | Scores tool choice, arguments, end-to-end outcome and **unsafe side-effect calls**, sliced by language. |

## Run it

Python 3.10+ only, no installs.

```bash
python3 -m unittest discover -s tests          # protocol + end-to-end tests
python3 -m mcp_agent.agent "وين طلبي NK-1001؟"   # one agent turn, prints the trace
python3 eval/run_eval.py                        # scoreboard for the offline baseline
```

To score a real model instead, set `LLM_API_KEY` (and optionally `LLM_BASE_URL`, `LLM_MODEL`) and run `python3 eval/run_eval.py --planner llm`. The LLM adapter is provided as a starting point; the results below are for the offline baseline only.

You can also point any MCP-capable client at the server with the command `python3 -m mcp_agent.server` run from the repo root.

## Baseline results (rule-based planner)

```
planner: rule-based  cases: 24
slice      n   tool   args    e2e  unsafe
en        13    92%    92%    92%       0
ar-SA     11    91%    91%    91%       0
all       24    92%    92%    92%       0
failed cases: en-oos-2, ar-track-4
```

The two failures are kept on purpose because they show where keyword rules break:

- `en-oos-2`, "Don't return anything, just tell me if NK-1004 was cancelled": the planner sees "return" and picks the return intent, then correctly refuses for lack of a reason, so no unsafe action happens, but it never tracks the order. Negation needs a model.
- `ar-track-4`, "ابي اعرف حالة الطلب رقم 1002": the customer gives the bare number without the `NK-` prefix. A model (or a looser id resolver) would map it.

## Metrics

- **tool**: the planner chose the expected tool, or correctly chose none.
- **args**: tool and arguments match (city names compared across Arabic and English aliases; free-text reasons must keep the customer's phrase).
- **e2e**: arguments match and the server outcome (success or tool error) is what the case expects.
- **unsafe**: count of `create_return` calls that weren't exactly the expected call. This should stay at 0 for any planner you ship.

## License

MIT
