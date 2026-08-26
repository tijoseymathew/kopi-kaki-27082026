"""`stall chat --cli` — the local loop in the terminal. You play the customer.

The browser is the front door (see web.py); this is the same loop
without the panel, for a box with no browser or a preference. Both mint
their own conversation, tick the same practice clock and price at the
same till.

After every turn you see exactly what the grader would see: the resolved
order (real menu item or UNRESOLVED), prices, promotions, and tokens.
There is no local test set; imagining customers is the skill.

The stock board here is a *practice* board. It is rolled fresh for each
conversation, it moves under you the way the graded one does — a supply
out, a drink down to its last cup, a walk-up customer coming for it —
and it shares none of its numbers with the hidden run. Holds on it are
real: chope the cup and the walk-up cannot have it.
"""

from __future__ import annotations

import pathlib
import secrets
import shutil
import sys

from . import api, customers
from .proxy import MeterProxy
from .runner import core


def load_agent(agent_dir: pathlib.Path, hook=None) -> core.Host:
    """A Host over the student's directory. Both front doors use this.

    The import itself is deferred to the first build, because that is
    where the shared core does it and where the stall does it too. So
    the only case refused here is the one the core cannot phrase better
    than we can: there is no agent.py at all.
    """
    path = agent_dir / "agent.py"
    if not path.exists():
        sys.exit(f"{path} not found — run `stall init` first")
    return core.Host(str(agent_dir), hook)


def start_agent(host: core.Host, config: dict) -> None:
    """The first build, which is also the import.

    A shape problem — no `Agent`, or a method with the wrong number of
    parameters — is a sentence the student can act on, and it is the
    same sentence `stall submit` would have answered with, because the
    check is the same code. An `agent.py` that blows up on import is
    their own traceback and gets out of the way of nothing.
    """
    try:
        host.new(config)
    except core.ShapeError as e:
        sys.exit(str(e))


def mint_conversation(env: dict) -> tuple[str, str]:
    """A fresh conversation token, and the stock URL that addresses it.

    Sixteen hex characters, because the stall checks the token against
    ^[a-f0-9]{16}$ before it becomes a filename. Minted per conversation
    exactly as the grader mints one per case, so `/new` really is a new
    customer walking up rather than the last one's holds and turn count
    inherited.
    """
    conv = secrets.token_hex(8)
    return conv, f"{env['STALL_URL']}/stock?conv={conv}"


def _banner_line(stall_url: str, conv: str) -> str:
    """Which practice board this is, in one line.

    A GET does not move the clock, so asking costs the student nothing
    — and it is what creates the world, so the answer is the mode the
    conversation is actually frozen at rather than whatever level the
    stall reaches later.
    """
    try:
        status, board = api.get_json_status(f"{stall_url}/stock?conv={conv}")
    except api.StallError:
        return "practice board: the stall is not answering."
    if status != 200:
        return "practice board: the stall is not answering."
    if board.get("day") == "busy":
        return ("practice board: a busy day — something is out, something is "
                "down to its last cup, and a walk-up is coming for it.")
    return ("practice board: a quiet day — everything in stock, and nothing "
            "moves. It runs low once the stall reaches level 3.")


def _tick(stall_url: str, conv: str) -> None:
    """One customer turn on the practice clock, before the agent hears
    the message — where the grader ticks it too. A failure warns and the
    turn proceeds: the stall being briefly unreachable costs a student
    the walk-up, not their turn."""
    try:
        status, out = api.post_json(f"{stall_url}/practice/turn",
                                    {"conv": conv})
        if status != 200:
            print(f"  (practice clock stuck: {out.get('error', out)})",
                  file=sys.stderr)
    except api.StallError as e:
        print(f"  (practice clock stuck: {e})", file=sys.stderr)


def _show_order(stall_url: str, order, conv: str):
    items = order.get("items", []) if isinstance(order, dict) else order
    if not items:
        print("  (order is empty)")
        return
    status, resolved = api.post_json(
        f"{stall_url}/resolve", {"items": items, "conv": conv})
    if status != 200:
        print(f"  resolve failed: {resolved}")
        return
    for line in resolved["lines"]:
        if line["canonical"] is None:
            print(f"  ✗ {line['given']!r:30}  UNRESOLVED — the stall sells no such drink")
        else:
            note = "" if line["available"] in (True, None) else "  [SOLD OUT]"
            print(f"  ✓ {line['given']!r:30}  {line['qty']} × {line['canonical']}"
                  f"  ${line['unit_cents'] / 100:.2f}{note}")
    for d in resolved["discounts"]:
        print(f"    promo: {d['name']}  -${d['cents'] / 100:.2f}")
    print(f"    till total: ${resolved['total_cents'] / 100:.2f}")


def chat(agent_dir: str, env: dict, reset_memory: bool):
    agent_dir = pathlib.Path(agent_dir)
    customer_id = customers.draw()
    if not env.get("LLM_API_KEY"):
        print("warning: LLM_API_KEY is not set — your agent's LLM calls will fail",
              file=sys.stderr)

    memory_dir = agent_dir / ".stall" / "memory"
    if reset_memory and memory_dir.exists():
        shutil.rmtree(memory_dir)
        print("memory wiped.")
    memory_dir.mkdir(parents=True, exist_ok=True)

    host = load_agent(agent_dir)
    proxy = MeterProxy(env["LLM_BASE_URL"], env.get("EMBEDDING_BASE_URL", ""))
    conv, stock_url = mint_conversation(env)
    config = {
        "llm_base_url": proxy.base_url,
        "llm_model": env["LLM_MODEL"],
        "llm_api_key": env.get("LLM_API_KEY", ""),
        # Same proxy as llm_base_url — it dispatches /embeddings to its
        # own EMBEDDING_BASE_URL — named separately so an agent's config
        # never has to assume the two are the same address.
        "embedding_base_url": proxy.base_url,
        "embedding_api_key": env.get("LLM_API_KEY", ""),
        "embedding_model": env.get("EMBEDDING_MODEL", ""),
        "stock_url": stock_url,
        "memory_dir": str(memory_dir),
        "customer_id": customer_id,
    }

    print(f"You are the customer. Your agent runs {env['LLM_MODEL']} — "
          f"graded runs use the stall's model.\n"
          f"customer_id={customer_id}\n"
          f"{_banner_line(env['STALL_URL'], conv)}\n"
          f"/new starts a fresh conversation, /exit leaves.\n")

    start_agent(host, config)
    conversation_tokens = 0
    try:
        while True:
            try:
                line = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            if line == "/exit":
                break
            if line == "/new":
                # The token first: `/new` rebuilds the Agent from this
                # same dict, so a stale stock_url would hand the new
                # customer the last one's holds and turn count.
                conv, config["stock_url"] = mint_conversation(env)
                config["customer_id"] = customer_id = customers.draw()
                host.new(config)
                conversation_tokens = 0
                proxy.total_tokens = 0
                print(f"(fresh conversation — {customer_id} at the "
                      f"counter, new Agent and a new practice board, "
                      f"same memory dir)")
                print(_banner_line(env["STALL_URL"], conv) + "\n")
                continue
            _tick(env["STALL_URL"], conv)
            before = proxy.total_tokens
            try:
                reply = host.turn(line)["reply"]
            except Exception:
                import traceback
                traceback.print_exc()
                print("(your agent raised — in a graded run this case would score 0)")
                continue
            turn_tokens = proxy.total_tokens - before
            conversation_tokens = proxy.total_tokens
            print(f"\nagent> {reply}\n")
            try:
                order = host.order()["order"]
            except Exception:
                import traceback
                traceback.print_exc()
                continue
            _show_order(env["STALL_URL"], order, conv)
            print(f"    tokens: {turn_tokens} this turn, "
                  f"{conversation_tokens} this conversation\n")
    finally:
        proxy.close()
