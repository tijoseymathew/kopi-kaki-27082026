"""Run a turn against a student's Agent. The one implementation of it.

This module is shared verbatim between the two repos: the stall server
grades through it, and `stall chat` drives the local panel through the
same code, so a submission that runs locally is byte-for-byte the
submission that grades. The server's copy is the source; the client's
`stall/runner/` is a directory copy, and a test in each repo fails on
any difference between them.

What lives here is only the parts that must not differ:

  * loading `agent.py` out of a submission directory,
  * building an `Agent` from a config dict,
  * calling `handle_turn` and `current_order`,
  * turning an exception from any of the three into the `{"error": ...}`
    the grader scores,
  * and the four routes that expose all of the above.

What deliberately does not live here: stock forwarding and LLM
metering. Local and graded differ substantially in both — a practice
board against a graded world, a student's own key against a per-run
token — and sharing them would mean a flag per difference.

The routes, all JSON in and JSON out:

  GET  /health   {"ok": true}  once the socket is up, before any Agent
  POST /new      {"config": {...}}   -> {"ok": true}     a fresh Agent
  POST /turn     {"message": "..."}  -> {"reply": "..."}
  POST /order                        -> {"order": {...}}

`agent.py` is imported at the first `/new`, not at startup: the server
has to be listening before it can report anything at all, and a failed
import is an answer rather than a silence. Every `/new` after a failed
import fails the same way, because the failure is remembered.

Errors divide in two, and the division is load-bearing:

  200 with {"error": "<traceback>"}   the submission raised. It is data,
                                     and the grader scores it as a lost
                                     case.
  500 with {"error": "..."}           the harness broke. Not the
                                     student's fault, and the caller
                                     treats it as its own bug.

An optional `hook` brackets every call into student code. The grader
passes None — `events.py` installs an audit hook on `open()` and swaps
`sys.stdout` for the duration of a turn, which is process-global
machinery that must not exist in a graded run. The client passes its
panel binding. The interface is two methods:

    hook.turn_started(op)          op is "new" | "turn" | "order"
    hook.turn_finished(op, error)  error is the exception, or None
"""

from __future__ import annotations

import importlib.util
import json
import traceback
from http.server import BaseHTTPRequestHandler

# (name, parameter count including self) — the whole of the contract
# agent.py is held to, checked once on the class rather than by a
# separate importer. Two importers of the same file is precisely where
# "the structural check passed and then every case scored zero" comes
# from.
SIGNATURE = (("__init__", 2), ("handle_turn", 2), ("current_order", 1))


class ShapeError(Exception):
    """agent.py loaded, but Agent is not the shape the stall calls.

    Reported by its message alone. A traceback here would be a tour of
    this file, and the student wrote none of it.
    """


class Host:
    """One submission, and at most one live Agent built from it."""

    def __init__(self, submission_dir: str, hook=None):
        self.submission_dir = submission_dir
        self.hook = hook
        self.agent_cls = None
        self.load_error: str | None = None
        self.agent = None

    # -- the submission -----------------------------------------------------

    def load(self) -> None:
        """Import agent.py and check Agent's shape. Idempotent, and a
        failure is remembered: the second case must not re-run a module
        whose import already had side effects."""
        if self.agent_cls is not None:
            return
        if self.load_error is not None:
            raise ShapeError(self.load_error)
        try:
            self.agent_cls = _import_agent(self.submission_dir)
        except ShapeError as e:
            self.load_error = str(e)
            raise
        except Exception:
            self.load_error = traceback.format_exc()
            raise

    # -- the three calls ----------------------------------------------------

    def new(self, config: dict):
        self.load()
        with _bracket(self.hook, "new"):
            self.agent = self.agent_cls(config)
        return {"ok": True}

    def turn(self, message: str):
        with _bracket(self.hook, "turn"):
            reply = self._agent().handle_turn(message)
        return {"reply": str(reply)}

    def order(self):
        with _bracket(self.hook, "order"):
            order = self._agent().current_order()
        return {"order": order}

    def _agent(self):
        if self.agent is None:
            raise ShapeError("no Agent yet — POST /new first")
        return self.agent


class _bracket:
    """Tells the hook a call into student code began and ended.

    A context manager rather than a try/except around each call site,
    so that the three of them read the same and none can forget the
    finish. Nothing is swallowed: the exception goes on to be formatted
    by the route.
    """

    def __init__(self, hook, op: str):
        self.hook = hook
        self.op = op

    def __enter__(self):
        if self.hook is not None:
            self.hook.turn_started(self.op)

    def __exit__(self, kind, value, tb):
        if self.hook is not None:
            self.hook.turn_finished(self.op, value)
        return False


def _import_agent(submission_dir: str):
    spec = importlib.util.spec_from_file_location(
        "student_agent", submission_dir + "/agent.py")
    if spec is None or spec.loader is None:
        raise ShapeError(f"no agent.py in {submission_dir}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return agent_class(module)


def agent_class(module):
    """The submission's Agent, checked. Raises ShapeError.

    Split out from the import so the client can hold a module it loaded
    its own way to exactly the same contract.
    """
    import inspect

    agent_cls = getattr(module, "Agent", None)
    if not isinstance(agent_cls, type):
        raise ShapeError("agent.py does not define a class Agent")
    for name, argc in SIGNATURE:
        fn = getattr(agent_cls, name, None)
        if not callable(fn):
            raise ShapeError(f"Agent.{name} is missing")
        params = [p for p in inspect.signature(fn).parameters.values()
                  if p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)]
        if len(params) != argc:
            raise ShapeError(
                f"Agent.{name} should take {argc} parameters, "
                f"has {len(params)}")
    return agent_cls


def failure(exc: BaseException) -> dict:
    """The {"error": ...} body a raise from student code becomes.

    A ShapeError is ours to phrase and arrives as its message; anything
    else is the submission's own and arrives whole, because the
    traceback is the answer the student needs.
    """
    if isinstance(exc, ShapeError):
        return {"error": str(exc)}
    return {"error": traceback.format_exc()}


def make_handler(host: Host):
    """The four routes, over whatever socket the caller has bound."""

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            """Silence. stderr is the grading script's progress channel
            and an access line on it is not JSON."""

        def _send(self, status: int, payload: dict) -> None:
            try:
                body = json.dumps(payload).encode()
            except (TypeError, ValueError):
                # current_order returns whatever the student returns.
                status, body = 200, json.dumps(
                    {"error": "current_order did not return JSON"}).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json_body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw or b"{}")
            return data if isinstance(data, dict) else {}

        def do_GET(self):
            if self.path == "/health":
                self._send(200, {"ok": True})
            else:
                self._send(404, {"error": f"no route {self.path}"})

        def do_POST(self):
            try:
                data = self._json_body()
            except (ValueError, OSError) as e:
                self._send(500, {"error": f"harness could not read body: {e}"})
                return
            try:
                call = {"/new": lambda: host.new(data.get("config") or {}),
                        "/turn": lambda: host.turn(str(data.get("message", ""))),
                        "/order": host.order}[self.path]
            except KeyError:
                self._send(404, {"error": f"no route {self.path}"})
                return
            try:
                self._send(200, call())
            except Exception as e:            # the submission raised
                self._send(200, failure(e))

    return Handler
