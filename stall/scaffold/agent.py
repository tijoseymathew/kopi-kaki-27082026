"""Your stall agent. The whole contract is these three methods.

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
