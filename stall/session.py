"""One student, one browser tab, one conversation at a time.

The chat UI is a thin skin on this object: the browser posts what the
customer says, the session runs the turn exactly as the REPL does — tick
the practice clock, hand the message to the agent, price the order at
the till — and hands back everything the page draws, including the
event log of what the agent did on the way.

The agent is built **once, when the server starts**. A student who has
edited `agent.py` stops the server and runs `stall chat` again, and
that restart is the whole of the story: a new process reads the file,
resolves the environment, and starts the conversation from the same
clean slate a graded run starts from. Nothing here reaches back into a
running process to swap code underneath it.

It is built and driven through `runner/core.py`, which is a verbatim
copy of the stall server's own — so "run a turn against a student's
Agent" has one implementation, and a submission that runs here is
byte-for-byte the submission that grades. Everything else on this page
is the panel, which grading does not have: the tick, the walk-up
narration, the till preview, the turn record.
"""

from __future__ import annotations

import pathlib
import shutil
import sys
import threading
import time
import traceback

from . import api, customers, events
from .proxy import MeterProxy
from .repl import load_agent, mint_conversation, start_agent
from .runner import core

LEVELS = [
    (1, "Just Ask"), (2, "Ground It"), (3, "Hold It"),
    (4, "Package It"), (5, "Remember It"),
]


class _PanelHook:
    """What the SEE INSIDE panel hears from inside a call.

    The core brackets every call into the student's code with this, and
    it is the whole of what the panel needs from in there: a raise, as
    it happens, with the traceback still whole. Everything else the
    panel shows — the LLM round trips, the stock calls, the prints, the
    files — is observed from outside the call and needs no hook.

    The grading script passes `None` instead, so none of this exists in
    a graded run. That is the point of the hook being optional rather
    than the core importing `events` itself: `events.py` installs an
    audit hook on `open()` and swaps `sys.stdout` for the duration of a
    turn, and that is process-global machinery a graded run must not
    have.
    """

    def __init__(self, agent_dir: pathlib.Path):
        self.agent_dir = agent_dir
        self.crash = ""

    def turn_started(self, op: str) -> None:
        pass

    def turn_finished(self, op: str, error: BaseException | None) -> None:
        if error is None:
            return
        with events.muted():  # rendering it opens agent.py; that is us
            self.crash = "".join(traceback.format_exception(error))
        title = ("current_order() raised" if op == "order"
                 else _exception_line(self.crash))
        events.add("raise", title, _agent_line(self.crash, self.agent_dir),
                   self.crash)


class ChatSession:
    """The conversation the page is looking at, and the agent behind it."""

    def __init__(self, agent_dir: str, env: dict, reset_memory: bool,
                 stock_url):
        self.agent_dir = pathlib.Path(agent_dir)
        self.env = env
        self.customer_id = ""
        self.stall_url = env["STALL_URL"]
        # `stock_url(conv)` addresses this process, not the stall: the
        # agent's board reads come back through us so the UI can show
        # them. web.py forwards them on.
        self._stock_url = stock_url
        self._lock = threading.Lock()

        self.memory_dir = self.agent_dir / ".stall" / "memory"
        if reset_memory and self.memory_dir.exists():
            shutil.rmtree(self.memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.hook = _PanelHook(self.agent_dir)
        self.host = load_agent(self.agent_dir, self.hook)
        self.proxy = MeterProxy(env["LLM_BASE_URL"],
                                env.get("EMBEDDING_BASE_URL", ""), record=True)
        self.stall = _stall_state(self.stall_url)
        self.submission: Submission | None = None
        self.turns: list[dict] = []
        self.first = True
        self.new_conversation()

    # -- the conversation ---------------------------------------------------

    def new_conversation(self) -> None:
        """A new customer walks up: a new face at the counter, new token,
        new board, new Agent, and the same memory directory — which is
        the point of Level 5. The face is drawn before the Agent is
        built, because the id goes into the config it is built from."""
        with self._lock:
            self.customer_id = customers.draw()
            self.conv, _ = mint_conversation(self.env)
            self.turns = []
            self.proxy.total_tokens = 0
            self.proxy.calls = 0
            self.holds_seen: dict[str, int] = {}
            if self.first:
                # The very first build is also the import, and a shape
                # problem there is a sentence rather than a traceback —
                # the same sentence `stall submit` would answer with.
                # After it, agent.py is loaded and only the student's own
                # __init__ can fail, which the panel reports like any
                # other raise.
                start_agent(self.host, self._config())
                self.first = False
            else:
                self.host.new(self._config())
            self.board = self._board()
            self.stall = _stall_state(self.stall_url)

    def _config(self) -> dict:
        return {
            "llm_base_url": self.proxy.base_url,
            "llm_model": self.env["LLM_MODEL"],
            "llm_api_key": self.env.get("LLM_API_KEY", ""),
            # Same proxy as llm_base_url — it dispatches /embeddings to
            # its own EMBEDDING_BASE_URL — named separately so an
            # agent's config never has to assume the two are the same
            # address.
            "embedding_base_url": self.proxy.base_url,
            "embedding_api_key": self.env.get("LLM_API_KEY", ""),
            "embedding_model": self.env.get("EMBEDDING_MODEL", ""),
            "stock_url": self._stock_url(self.conv),
            "memory_dir": str(self.memory_dir),
            "customer_id": self.customer_id,
        }

    def say(self, text: str) -> dict:
        """One customer turn, start to finish.

        Blocks until the agent has replied, and the whole log lands with
        it. Nothing reports progress on the way, because the page that
        would have to ask for it is a page redrawing itself under
        someone who is reading — see the note at the top of app.js.
        """
        with self._lock:
            log = events.TurnLog()
            events.CURRENT = log
            started = time.monotonic()
            before = self.proxy.total_tokens
            tap = events.PrintTap(sys.stdout, self.agent_dir)
            try:
                shelf = self._tick()
                real_stdout, sys.stdout = sys.stdout, tap
                try:
                    reply, error = self._handle(text)
                finally:
                    sys.stdout = real_stdout
                    tap.close()
                order = self._order()
                self.board = self._board()
                self._world(shelf, self.board)
                events.settle_file_events(log)
                turn = {
                    "you": text, "reply": reply, "error": error,
                    "tokens": self.proxy.total_tokens - before,
                    "ms": int((time.monotonic() - started) * 1000),
                    "events": log.events(),
                    "order": order,
                }
            finally:
                events.CURRENT = None
            self.turns.append(turn)
            return turn

    def _handle(self, text: str) -> tuple[str | None, str | None]:
        """The core makes the call; the hook has already logged a raise
        by the time one reaches here."""
        try:
            return self.host.turn(text)["reply"], None
        except Exception:
            return None, _their_frames(self.hook.crash, self.agent_dir)

    def _order(self) -> dict:
        """The till preview: the same call the REPL makes, so the chit
        and the terminal agree about what was ordered."""
        try:
            order = self.host.order()["order"]
        except Exception:
            return {"lines": [], "discounts": [], "total_cents": 0,
                    "error": "current_order() raised"}
        items = order.get("items", []) if isinstance(order, dict) else order
        if not isinstance(items, list) or not items:
            return {"lines": [], "discounts": [], "total_cents": 0}
        try:
            status, resolved = api.post_json(
                f"{self.stall_url}/resolve",
                {"items": [i for i in items if isinstance(i, dict)],
                 "conv": self.conv})
        except api.StallError as e:
            return {"lines": [], "discounts": [], "total_cents": 0,
                    "error": str(e)}
        if status != 200:
            return {"lines": [], "discounts": [], "total_cents": 0,
                    "error": resolved.get("error", str(resolved))}
        return resolved

    # -- the practice world -------------------------------------------------

    def _board(self) -> dict:
        """The practice board as it stands. A GET does not move the
        clock, so the UI may ask as often as it likes."""
        try:
            status, board = api.get_json_status(
                f"{self.stall_url}/stock?conv={self.conv}")
        except api.StallError as e:
            return {"error": str(e), "rows": [], "held": {}}
        if status != 200:
            return {"error": board.get("error", str(board)), "rows": [],
                    "held": {}}
        held = {h["item"]: h["qty"] for h in board.get("held_for_you", [])}
        return {"day": board.get("day"), "rows": board.get("board", []),
                "held": held}

    def _tick(self) -> dict:
        """One customer turn on the practice clock, before the agent
        hears the message — where the grader ticks it too. The board is
        read on both sides of the tick, because the tick is the only
        thing that moves the walk-up: whatever changed across it, the
        walk-up did."""
        shelf = self._board()
        try:
            status, out = api.post_json(f"{self.stall_url}/practice/turn",
                                        {"conv": self.conv})
            if status != 200:
                events.add("world", "the practice clock is stuck",
                           str(status), str(out.get("error", out)))
                return shelf
        except api.StallError as e:
            events.add("world", "the practice clock is stuck", "", str(e))
            return shelf
        after = self._board()
        self._walkup(shelf, after)
        return after

    def _walkup(self, before: dict, after: dict) -> None:
        """Who else was at the counter. A row that fell across the tick
        is a walk-up customer buying a cup nobody had held."""
        was = {r["item"]: r["left"] for r in before.get("rows", [])}
        diff = [[r["item"], f"{was[r['item']]} left",
                 f"{r['left']} left" if r["left"] else "OUT"]
                for r in after.get("rows", [])
                if r["item"] in was and r["left"] < was[r["item"]]]
        if not diff:
            return
        names = ", ".join(d[0] for d in diff)
        events.add(
            "world", f"a walk-up customer bought the last {names}",
            "while you were talking",
            f"the walk-up takes what nobody has held. Cups you chope with\n"
            f"POST {{'name': ..., 'qty': ...}} to stock_url are off the\n"
            f"shelf and under your customer's name — this one was not.",
            diff)

    def _world(self, before: dict, after: dict) -> None:
        """Holds that landed during the turn: the cup is off the shelf
        and under this customer's name, and the walk-up cannot have it."""
        for item, qty in after.get("held", {}).items():
            gained = qty - before.get("held", {}).get(item, 0)
            if gained > 0:
                left = next((r["left"] for r in after.get("rows", [])
                             if r["item"] == item), None)
                events.add(
                    "world", f"{gained} × {item} is choped for this customer",
                    "held to the end of the conversation",
                    f"held: {qty}\nstill on the shelf for anyone else: {left}\n\n"
                    f"A held cup still prices as available at the till, and\n"
                    f"the walk-up customer cannot buy it.",
                    [[item, f"{before.get('held', {}).get(item, 0)} held",
                      f"{qty} held — by you"]])

    # -- what the page draws ------------------------------------------------

    def state(self) -> dict:
        """What the page draws.

        Tokens, and no money made out of them: the leaderboard ranks on
        revenue and then on the token count itself (store.py:277), so
        the count is the number a student is being judged by. The one
        cost figure the page shows is the one the stall reports about a
        finished run, in its own words.
        """
        return {
            "stall": self.stall,
            "conv": self.conv,
            "customer_id": self.customer_id,
            "agent_dir": str(self.agent_dir),
            "model": self.env["LLM_MODEL"],
            "turns": self.turns,
            "board": self.board,
            "tokens": self.proxy.total_tokens,
            "submit": self.submission.state() if self.submission else None,
        }

    def close(self) -> None:
        self.proxy.close()


def _stall_state(stall_url: str) -> dict:
    """Level, model and rate, or the reason the page cannot say. Asked
    once per conversation: `/new` is how a student picks up a level the
    stall advanced to while they were mid-conversation, which is exactly
    what the practice board does too."""
    try:
        status, state = api.get_json_status(f"{stall_url}/state")
    except api.StallError as e:
        return {"reachable": False, "error": str(e), "url": stall_url,
                "level": 0, "level_name": "the stall is not answering"}
    if status != 200:
        return {"reachable": False, "error": str(state), "url": stall_url,
                "level": 0, "level_name": "the stall is not answering"}
    level = int(state.get("level") or 0)
    names = dict(LEVELS)
    return {"reachable": True, "url": stall_url, "level": level,
            "level_name": names.get(level, "—"),
            "model": state.get("model"), "open": state.get("open"),
            "max_runs": state.get("max_runs"),
            "cooldown_seconds": state.get("cooldown_seconds")}


def _their_frames(crash: str, agent_dir: pathlib.Path) -> str:
    """The traceback as the bubble shows it: from the first line of the
    student's own code down. The frames above it are this client's, and
    reading a crash whose top frame is `session.py` sends people looking
    for the bug in the wrong file. The panel keeps the whole thing.
    """
    lines = crash.splitlines()
    root = str(agent_dir.resolve())
    start = next((i for i, line in enumerate(lines)
                  if line.strip().startswith('File "') and root in line), None)
    if start is None:
        return crash
    return "\n".join([lines[0]] + lines[start:])


def _exception_line(crash: str) -> str:
    return crash.strip().splitlines()[-1][:160]


def _agent_line(crash: str, agent_dir: pathlib.Path) -> str:
    """The last frame inside the student's own code — the line they can
    actually go and fix, not the one in json/__init__.py."""
    root = str(agent_dir.resolve())
    found = ""
    for line in crash.splitlines():
        part = line.strip()
        if part.startswith('File "'):
            path = part.split('"')[1]
            if path.startswith(root):
                name = path.rsplit("/", 1)[-1]
                found = f"{name}:{part.rsplit('line ', 1)[-1].split(',')[0]}"
    return found


class Submission:
    """A graded run, from packing the files to the final numbers.

    It runs on its own thread because the page must stay usable while it
    happens: the room's whole rhythm is submit, keep talking to your
    agent, read the numbers when they land.
    """

    STEPS = ("pack", "join", "submit", "run")

    def __init__(self, stall_url: str, agent_dir: pathlib.Path, code: str,
                 name: str, on_join):
        self.stall_url = stall_url
        self.agent_dir = agent_dir
        self.code = code
        self.name = name
        self._on_join = on_join
        self._lock = threading.Lock()
        self._state = {"phase": "packing", "steps": [], "run_id": None,
                       "result": None, "error": None,
                       "structural_error": None, "needs": None,
                       "stall_name": None, "progress": None, "tokens": 0}
        threading.Thread(target=self._run, daemon=True).start()

    def state(self) -> dict:
        with self._lock:
            return dict(self._state, steps=list(self._state["steps"]))

    def _set(self, **fields) -> None:
        with self._lock:
            self._state.update(fields)

    def _step(self, text: str, ok: bool = True) -> None:
        with self._lock:
            self._state["steps"].append({"text": text, "ok": ok})

    def _run(self) -> None:
        try:
            files = pack(self.agent_dir)
            if not files:
                self._set(phase="error",
                          error=f"nothing to submit in {self.agent_dir}/")
                return
            size = sum(len(c) for c in files.values())
            self._step(f"{len(files)} files packed — "
                       f"{', '.join(sorted(files))} ({size / 1024:.1f} KB)")

            self._set(phase="joining")
            status, out = api.post_json(f"{self.stall_url}/join",
                                        {"code": self.code, "name": self.name})
            if status == 400:
                # The stall's own words: non-ASCII, too long, or already
                # another stall's. The page asks for another name.
                self._set(phase="needs", needs="name",
                          error=out.get("error", str(out)))
                return
            if status != 200:
                self._set(phase="needs" if status == 401 else "error",
                          needs="code" if status == 401 else None,
                          error=out.get("error", str(out)))
                return
            stall_name = out["stall"]
            self._on_join(self.code, stall_name)
            self._set(stall_name=stall_name)
            self._step(f"joined as {stall_name!r}")

            self._set(phase="submitting")
            status, out = api.post_json(
                f"{self.stall_url}/submit",
                {"code": self.code, "files": files})
            if status == 422:
                self._step("structural check failed", ok=False)
                self._set(phase="structural",
                          structural_error=out["structural_error"])
                return
            if status != 200:
                self._step("the stall refused the run", ok=False)
                self._set(phase="error", error=out.get("error", str(out)))
                return
            self._step("structural check passed — Agent class, both methods")
            self._step("memory left behind (graded runs start wiped)")
            run_id = out["run_id"]
            self._set(phase="running", run_id=run_id)

            while True:
                time.sleep(2)
                run = api.get_json(f"{self.stall_url}/runs/{run_id}")
                # `progress` is present only while the stall is actually
                # grading, and carries a case counter that moves every
                # case beside a revenue total that moves every fifth.
                # The page draws it; nothing here interprets it.
                self._set(status_text=run["status"],
                          progress=run.get("progress"),
                          tokens=run.get("tokens") or 0)
                if run["status"] in ("done", "failed"):
                    break
            if run["status"] == "failed":
                self._set(phase="error",
                          error=f"the stall broke, not you: {run.get('error')}")
                return
            self._step("the 25 customers have been and gone")
            self._set(phase="done", result=run)
        except api.StallError as e:
            self._set(phase="error", error=str(e))
        except Exception as e:  # a client bug is still the student's problem
            self._set(phase="error", error=f"{type(e).__name__}: {e}")


def pack(directory: pathlib.Path) -> dict[str, str]:
    """The submission: the same files `stall submit` sends, chosen by the
    same rule, so the button and the command cannot disagree."""
    files = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix in (".py", ".md", ".toml", ".lock") \
                and not {".stall", ".venv"} & set(path.parts):
            files[str(path.relative_to(directory))] = path.read_text()
    return files
