"""Your stall agent. The whole contract is these three methods.

config keys:
  llm_base_url  OpenAI-compatible endpoint. POST {llm_base_url}/chat/completions
                with {"model": ..., "messages": [...]} and header
                "Authorization: Bearer <llm_api_key>".
  llm_model     model name to put in the request body
  llm_api_key   key to use (during graded runs the stall injects one)

The stall speaks first and decides when the conversation ends. You only
ever reply. current_order() is read whenever the customer walks away —
it must hold the complete order: {"items": [{"name": str, "qty": int}]},
with modifiers baked into the name ("Kopi C Kosong Peng" is one item).
"""

import json
import urllib.request


class Agent:
    def __init__(self, config):
        self.config = config
        self._order = {"items": []}
        self._messages = []

        # ============================================================
        # PROMPT
        # ============================================================
        self._system_prompt = """You are a friendly Singapore hawker-stall agent.

You are taking a customer's food/drink order. The customer may speak
casually, use Singaporean English/Singlish, or make corrections.

Your job is to:
1. Understand what the customer wants.
2. Ask concise clarification questions when necessary.
3. Keep track of the complete current order.
4. Reply naturally and briefly, like a stall assistant.
5. Never claim an item was ordered unless the customer actually ordered it.

Order representation:
{"items": [{"name": str, "qty": int}]}

Modifiers must be baked into the item name. For example:
"Kopi C Kosong Peng" is one item name, not separate modifiers.

When the customer changes an order, update the order rather than
duplicating the old version.

At the end of every response, output a machine-readable order update
on a separate line using exactly this format:

ORDER: {"items": [...]}

The ORDER line must contain the COMPLETE current order, not only changes.
Do not put anything else after the ORDER line.

Your normal customer-facing response should come before the ORDER line.
"""

    def _call_llm(self):
        base_url = self.config["llm_base_url"].rstrip("/")
        url = base_url + "/chat/completions"

        messages = [{"role": "system", "content": self._system_prompt}]
        messages.extend(self._messages)

        payload = {
            "model": self.config["llm_model"],
            "messages": messages,
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.config["llm_api_key"],
            },
            method="POST",
        )

        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode("utf-8"))

        return data["choices"][0]["message"]["content"]

    def handle_turn(self, message):
        self._messages.append({
            "role": "user",
            "content": message,
        })

        response = self._call_llm()

        # Parse the model's complete order from the final ORDER line.
        lines = response.rstrip().splitlines()
        order_line_index = None

        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().startswith("ORDER:"):
                order_line_index = i
                break

        if order_line_index is not None:
            order_text = lines[order_line_index].strip()[len("ORDER:"):].strip()

            try:
                order = json.loads(order_text)
                if (
                    isinstance(order, dict)
                    and isinstance(order.get("items"), list)
                ):
                    self._order = order
            except (json.JSONDecodeError, TypeError):
                pass

            customer_reply = "\n".join(lines[:order_line_index]).strip()
        else:
            customer_reply = response.strip()

        self._messages.append({
            "role": "assistant",
            "content": response,
        })

        return customer_reply

    def current_order(self):
        return self._order
