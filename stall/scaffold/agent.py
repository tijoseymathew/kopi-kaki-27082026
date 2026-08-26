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


class Agent:
    def __init__(self, config):
        self.config = config

    def handle_turn(self, message):
        # The customer just said `message`. Say something back.
        return "Sorry ah, still setting up the stall."

    def current_order(self):
        return {"items": []}
