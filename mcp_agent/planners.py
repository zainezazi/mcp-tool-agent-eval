"""Planners decide which tool (if any) to call for a user message.

RuleBasedPlanner is an offline, deterministic baseline for English and Saudi-dialect
Arabic so the whole pipeline and eval run with no API key. LLMPlanner is an optional
adapter for any OpenAI-compatible chat-completions endpoint with tool calling.
"""
import json
import os
import re
import urllib.request

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
ORDER_RE = re.compile(r"\b(?:NK|nk)[-\s]?(\d{4})\b")

INTENTS = {
    "create_return": ["return", "refund", "send it back", "ارجع", "ارجاع", "إرجاع", "استرجاع", "ارد", "رجّع", "رجع"],
    "track_order": ["where is", "track", "status", "arrive", "وين طلب", "وين الطلب", "متى يوصل", "متى بيوصل",
                    "حالة الطلب", "طلبي", "الشحنة"],
    "list_branches": ["branch", "store near", "opening hours", "open", "فرع", "فروع", "يفتح", "تفتحون", "دوام"],
}
CITIES = ["jeddah", "riyadh", "dammam", "جدة", "جده", "الرياض", "الدمام"]
REASON_RE = re.compile(r"(?:because|since|عشان|لأن|لان|بسبب)\s+(.+)$", re.IGNORECASE)


def normalise(text: str) -> str:
    return text.translate(ARABIC_DIGITS).replace("أ", "ا").replace("إ", "ا").strip()


class RuleBasedPlanner:
    name = "rule-based"

    def plan(self, message: str, tools: list) -> dict:
        """Return {"tool": name, "arguments": {...}} or {"tool": None, "reply": "..."}."""
        text = normalise(message)
        low = text.lower()
        m = ORDER_RE.search(text)
        order_id = f"NK-{m.group(1)}" if m else None
        intent = next((i for i, kws in INTENTS.items() if any(k in low for k in kws)), None)
        if intent == "create_return":
            if not order_id:
                return {"tool": None, "reply": "Which order would you like to return? Please share the order id."}
            r = REASON_RE.search(text)
            if not r:
                return {"tool": None, "reply": "Sure. What's the reason for the return?"}
            return {"tool": "create_return", "arguments": {"order_id": order_id, "reason": r.group(1).strip()}}
        if intent == "track_order" or (order_id and intent is None):
            if not order_id:
                return {"tool": None, "reply": "Please share your order id (it looks like NK-1234)."}
            return {"tool": "track_order", "arguments": {"order_id": order_id}}
        if intent == "list_branches":
            city = next((c for c in CITIES if c in low), None)
            if not city:
                return {"tool": None, "reply": "Which city are you in?"}
            return {"tool": "list_branches", "arguments": {"city": city}}
        return {"tool": None, "reply": "I can help with orders, returns and branch hours."}


class LLMPlanner:
    """Optional: OpenAI-compatible tool calling. Needs LLM_API_KEY; LLM_BASE_URL and LLM_MODEL are optional."""
    name = "llm"

    def __init__(self):
        self.key = os.environ["LLM_API_KEY"]
        self.base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    def plan(self, message: str, tools: list) -> dict:
        body = {
            "model": self.model, "temperature": 0,
            "messages": [
                {"role": "system", "content": "You are a store support agent. Call a tool only when you have every "
                 "required argument from the user. Never open a return without an order id and a reason; ask instead."},
                {"role": "user", "content": message}],
            "tools": [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                        "parameters": t["inputSchema"]}} for t in tools],
        }
        req = urllib.request.Request(f"{self.base}/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {self.key}",
                                              "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            choice = json.load(resp)["choices"][0]["message"]
        calls = choice.get("tool_calls") or []
        if not calls:
            return {"tool": None, "reply": choice.get("content") or ""}
        fn = calls[0]["function"]
        return {"tool": fn["name"], "arguments": json.loads(fn["arguments"] or "{}")}
