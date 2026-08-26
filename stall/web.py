"""`stall chat` — the local loop, in a browser tab.

A small server on 127.0.0.1 that serves one page and answers it. It owns
the same three things the REPL owns — your Agent, a practice board, and
a metering proxy — and adds the one thing a terminal cannot show: what
your agent did between the customer's message and its reply, every LLM
round trip and stock call and print of it.

Three routes matter:

  /              the page
  /api/*         what the page asks for — state, say, new, submit
  /stock         your agent's board reads, forwarded to the stall

That last one is why `config["stock_url"]` points here rather than at
the stall: the calls arrive, get logged, and go on unchanged. Your agent
cannot tell the difference, and the graded run — where the same URL
points at the stall's own listener — behaves identically.

Edit `agent.py`, stop the server, run `stall chat` again: a new process
is the same clean slate the graded run starts from, and nothing is left
over from the code you just replaced.
"""

from __future__ import annotations

import json
import os
import pathlib
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import api, events
from .session import ChatSession, Submission

UI = pathlib.Path(__file__).resolve().parent / "ui"
TYPES = {".html": "text/html; charset=utf-8",
         ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8",
         ".svg": "image/svg+xml"}
DEFAULT_PORT = 7788


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # The page is the log; a second copy in the terminal is noise the
    # student's own prints have to compete with.
    def log_message(self, fmt, *args):
        pass

    @property
    def session(self) -> ChatSession:
        return self.server.session

    # -- plumbing -----------------------------------------------------------

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload) -> None:
        self._send(status, json.dumps(payload).encode(), "application/json")

    def _read_body(self) -> bytes:
        """Every byte the client sent, off the socket, whatever the route
        means to do with it.

        This is HTTP/1.1: the browser sends its requests down one
        connection it keeps open, so a body a route did not bother to
        read is still sitting there when the next request arrives. The
        server reads `{}POST /api/new HTTP/1.1` as one request line,
        answers 501 in HTML, and the page — which was expecting JSON —
        reports the server as stopped. It has not stopped; the last
        route just left two bytes behind.
        """
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    @staticmethod
    def _json_body(raw: bytes) -> dict:
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _split(self) -> tuple[str, str]:
        path, _, query = self.path.partition("?")
        return path, query

    # -- GET ----------------------------------------------------------------

    def do_GET(self):
        path, query = self._split()
        if path == "/" or path == "/index.html":
            self._static("index.html")
        elif path in ("/app.css", "/app.js"):
            self._static(path.lstrip("/"))
        elif path == "/stock":
            self._stock("GET", query, None)
        elif path == "/api/state":
            self._json(200, self._state())
        elif path == "/api/history":
            self._history()
        else:
            self._json(404, {"error": "not found"})

    def _static(self, name: str) -> None:
        file = UI / name
        if not file.exists():
            self._json(404, {"error": f"{name} is missing"})
            return
        self._send(200, file.read_bytes(),
                   TYPES.get(file.suffix, "application/octet-stream"))

    def _state(self) -> dict:
        state = self.session.state()
        state["identity"] = read_identity()
        return state

    def _history(self) -> None:
        """Every past submission for whoever `.stall-identity.json` says
        this is, straight from the stall's own `/runs/mine` — the same
        button `stall submit` prints as `stall history`, in the panel's
        own words instead of a terminal's."""
        code = str(read_identity().get("code") or "").strip()
        if not code:
            self._json(200, {"joined": False, "runs": []})
            return
        try:
            status, out = api.post_json(
                f"{self.session.stall_url}/runs/mine", {"code": code})
        except api.StallError as e:
            self._json(502, {"error": str(e)})
            return
        if status != 200:
            self._json(status, out)
            return
        self._json(200, {"joined": True, "runs": out["runs"]})

    # -- POST ---------------------------------------------------------------

    def do_POST(self):
        path, query = self._split()
        raw = self._read_body()  # first, and for every route — see _read_body
        if path == "/stock":
            self._stock("POST", query, raw)
        elif path == "/api/say":
            text = str(self._json_body(raw).get("text") or "").strip()
            if not text:
                self._json(400, {"error": "say something"})
                return
            self.session.say(text)
            self._json(200, self._state())
        elif path == "/api/new":
            self.session.new_conversation()
            self._json(200, self._state())
        elif path == "/api/submit":
            self._submit(self._json_body(raw))
        else:
            self._json(404, {"error": "not found"})

    def _submit(self, data: dict) -> None:
        """Start a graded run, or say what is still missing.

        The join code lives on a paper slip and the stall name is the
        one on the projector; the REPL prompts for both on the terminal,
        and this asks the page for them instead. Whatever the stall
        accepts is written to the same `.stall-identity.json`, so the
        button and `stall submit` remember one identity between them.
        """
        session = self.session
        running = session.submission
        if running and running.state()["phase"] in (
                "packing", "joining", "submitting", "running"):
            self._json(200, self._state())  # already in flight; page reopens it
            return
        ident = read_identity()
        code = str(data.get("code") or ident.get("code") or "").strip()
        name = str(data.get("name") or ident.get("name") or "").strip()
        if not code:
            self._json(200, dict(self._state(), submit={
                "phase": "needs", "needs": "code", "steps": [],
                "error": None, "run_id": None, "result": None,
                "structural_error": None, "stall_name": None}))
            return
        session.submission = Submission(
            session.stall_url, session.agent_dir, code, name, write_identity)
        self._json(200, self._state())

    # -- the agent's own stock calls, on their way to the stall -------------

    def _stock(self, method: str, query: str, body: bytes | None) -> None:
        """Forward, log, answer. The reply the agent gets is byte for
        byte the stall's, including its refusals: a proxy that repaired
        anything here would be teaching the student's agent to depend on
        a repair the graded run does not make."""
        url = f"{self.session.stall_url}/stock?{query}"
        payload = None
        if body:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = None
        started = time.monotonic()
        try:
            status, raw = api._request(url, payload)
        except api.StallError as e:
            events.add("tool", f"{method} /stock — the stall did not answer",
                       "", str(e))
            self._json(502, {"error": str(e)})
            return
        ms = int((time.monotonic() - started) * 1000)
        if method == "GET":
            events.add("tool", "GET /stock  — read the board",
                       f"{status} · {ms}ms",
                       f"GET {_hide_conv(url)}\n\n{_board_text(raw)}")
        else:
            events.add("tool", f"POST /stock  — {_hold_title(payload, raw)}",
                       f"{status} · {ms}ms",
                       f"POST {_hide_conv(url)}\n→ {json.dumps(payload)}\n"
                       f"← {events.pretty(raw)}")
        self._send(status, raw, "application/json")


def _hide_conv(url: str) -> str:
    """The conversation token is 16 characters of noise in every line of
    the log; the first eight are enough to tell two apart."""
    head, _, query = url.partition("?")
    params = urllib.parse.parse_qs(query)
    conv = (params.get("conv") or [""])[0]
    return f"{head}?conv={conv[:8]}…" if conv else url


def _board_text(raw: bytes) -> str:
    """The board as a board: one row per drink, the way the student
    reads it on the wall."""
    try:
        data = json.loads(raw)
        rows = data["board"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return events.pretty(raw)
    width = max((len(r["item"]) for r in rows), default=0)
    lines = [f"day: {data.get('day', '?')}"]
    lines += [f"  {r['item']:<{width}}  {r['left']:>3} left"
              f"{'' if r['left'] else '   ← OUT'}" for r in rows]
    for held in data.get("held_for_you", []):
        lines.append(f"  held for this customer: {held['qty']} × {held['item']}")
    return "\n".join(lines)


def _hold_title(payload: dict | None, raw: bytes) -> str:
    want = f"{(payload or {}).get('qty', '?')} × {(payload or {}).get('name', '?')}"
    try:
        answer = json.loads(raw)
    except json.JSONDecodeError:
        return f"hold {want}"
    if answer.get("held") is True:
        return f"choped {want}"
    return f"hold {want} refused — {answer.get('reason', 'no reason given')}"


# ── the identity on disk, shared with `stall submit` ──────────────────

def _identity_path() -> pathlib.Path:
    from .cli import IDENTITY
    return IDENTITY


def read_identity() -> dict:
    path = _identity_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def write_identity(code: str, name: str) -> None:
    ident = read_identity()
    ident["code"], ident["name"] = code, name
    _identity_path().write_text(json.dumps(ident))


# ── running it ───────────────────────────────────────────────────────

def forwarded_url(port: int) -> str | None:
    """Where a Codespace's browser has to go instead of 127.0.0.1.

    Codespaces forwards the port and serves it from a URL of its own;
    printing the loopback address there sends students to a page their
    laptop cannot reach. The two variables are set inside every
    Codespace and nowhere else, so this is None on a normal machine.
    """
    name = os.environ.get("CODESPACE_NAME")
    domain = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN")
    return f"https://{name}-{port}.{domain}" if name and domain else None


def build(agent_dir: str, env: dict, reset_memory: bool,
          port: int = DEFAULT_PORT, host: str = "127.0.0.1"):
    """Bind first, then build the session: the agent's `stock_url` has to
    name the port we actually got."""
    try:
        httpd = ThreadingHTTPServer((host, port), Handler)
    except OSError:
        # Someone else has 7788 — very often the student's own last
        # `stall chat`, still running in another terminal. Take any port
        # rather than refusing to start.
        httpd = ThreadingHTTPServer((host, 0), Handler)
    bound = httpd.server_address[1]
    base = f"http://{host}:{bound}"
    session = ChatSession(agent_dir, env, reset_memory,
                          lambda conv: f"{base}/stock?conv={conv}")
    httpd.session = session
    events.watch_files(session.agent_dir, session.memory_dir)
    return httpd, base


def serve(agent_dir: str, env: dict, reset_memory: bool,
          port: int = DEFAULT_PORT, open_browser: bool = True) -> None:
    httpd, base = build(agent_dir, env, reset_memory, port)
    session = httpd.session
    bound = httpd.server_address[1]
    visit = forwarded_url(bound) or base
    print(f"\n  Kopi Kaki — your stall, in a browser:  {visit}\n")
    if visit != base:
        print(f"  (this Codespace forwards {base}; the tab has to use the "
              f"address above)")
    print(f"  you are the customer · customer_id={session.customer_id} · "
          f"model {env['LLM_MODEL']}")
    print("  (+ NEW draws another face from the counter — same memory dir, "
          "which is the Level 5 test)")
    if session.stall["reachable"]:
        print(f"  stall level {session.stall['level']} — "
              f"{session.stall['level_name']}   ({session.stall['url']})")
    else:
        print(f"  the stall is not answering at {session.stall['url']} — "
              f"the chat still runs, the till and the board do not")
    print("\n  edited agent.py?  Ctrl-C here, then `stall chat` again — "
          "a restart is how\n  new code, and a new pyproject.toml, get "
          "picked up.\n")
    if not env.get("LLM_API_KEY"):
        print("  warning: LLM_API_KEY is not set — your agent's LLM calls "
              "will fail\n")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(visit)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstall chat stopped.")
    finally:
        httpd.shutdown()
        session.close()
