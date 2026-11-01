"""Tool implementations for the fictional 'Nakheel Store' (synthetic data only)."""
import datetime as dt
import json
import pathlib

DATA = json.loads((pathlib.Path(__file__).resolve().parent.parent / "data" / "store.json").read_text(encoding="utf-8"))

CITY_ALIASES = {"jeddah": "Jeddah", "جدة": "Jeddah", "جده": "Jeddah",
                "riyadh": "Riyadh", "الرياض": "Riyadh", "الرياظ": "Riyadh",
                "dammam": "Dammam", "الدمام": "Dammam"}


class ToolError(Exception):
    pass


def normalise_city(city: str) -> str:
    key = (city or "").strip().lower()
    if key in CITY_ALIASES:
        return CITY_ALIASES[key]
    raise ToolError(f"unknown city: {city!r}")


def track_order(order_id: str) -> dict:
    order = DATA["orders"].get((order_id or "").upper())
    if not order:
        raise ToolError(f"order not found: {order_id!r}")
    return {"order_id": order_id.upper(), **order}


def list_branches(city: str) -> dict:
    c = normalise_city(city)
    return {"city": c, "branches": [b for b in DATA["branches"] if b["city"] == c]}


def create_return(order_id: str, reason: str, today: str = "2026-11-01") -> dict:
    order = track_order(order_id)
    if order["status"] != "delivered":
        raise ToolError(f"only delivered orders can be returned (status is {order['status']})")
    age = (dt.date.fromisoformat(today) - dt.date.fromisoformat(order["eta"])).days
    if age > DATA["return_window_days"]:
        raise ToolError("outside the return window")
    if not (reason or "").strip():
        raise ToolError("a reason is required")
    return {"order_id": order["order_id"], "return_id": f"RT-{order['order_id'][3:]}", "accepted": True}


TOOLS = {
    "track_order": {
        "fn": track_order,
        "description": "Look up the status and ETA of an order by its id (format NK-1234).",
        "inputSchema": {"type": "object", "properties": {"order_id": {"type": "string"}},
                        "required": ["order_id"]},
    },
    "list_branches": {
        "fn": list_branches,
        "description": "List store branches and opening hours in a Saudi city (Arabic or English city name).",
        "inputSchema": {"type": "object", "properties": {"city": {"type": "string"}},
                        "required": ["city"]},
    },
    "create_return": {
        "fn": create_return,
        "description": "Open a return for a delivered order inside the 14-day window. Side effect: creates a return.",
        "inputSchema": {"type": "object",
                        "properties": {"order_id": {"type": "string"}, "reason": {"type": "string"}},
                        "required": ["order_id", "reason"]},
    },
}
