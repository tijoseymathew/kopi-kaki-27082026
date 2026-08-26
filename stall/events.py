"""What your agent did between "you said" and "it replied".

The chat UI's whole reason to exist is the SEE INSIDE panel: every LLM
round trip, every stock call, every print, every file the agent touched,
in the order they happened. Nothing here instruments the student's code
— `agent.py` is theirs and stays untouched — so each source is observed
from the outside instead:

  llm          the metering proxy already sits in the middle (proxy.py)
  tool         `stock_url` points at this process, which forwards (web.py)
  print        stdout is replaced for the duration of the turn
  mem/skill    an audit hook sees every `open()` under my-stall/
  file         the same hook, for documents the agent reads on purpose
  world        the practice board is read before and after the turn
  raise        the traceback, when handle_turn blows up

One turn runs at a time — the UI will not send a second message while
the first is in flight — so the log being a module-level `CURRENT` is
enough to catch events raised on the proxy's threads as well as this
one. Outside a turn `CURRENT` is None and every source is a no-op.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import sys
import threading
import time

# The kinds the UI knows how to colour. Anything else is dropped rather
# than rendered as an unstyled row.
KINDS = ("llm", "tool", "print", "world", "skill", "mem", "file", "raise")

MAX_BODY = 6000

# What the panel is for is the documents a student's agent opens on
# purpose — the menu it grounded itself in, the promo poster, the skill
# it packaged, the memory it keeps. Everything else that passes through
# `open()` under my-stall/ is Python loading itself, and a Level 2 agent
# that imports one library would bury the turn under a hundred rows of
# site-packages. Two rules keep the panel readable, and both are about
# noise rather than secrecy:
#
#   1. directories that exist because a tool put them there
#   2. reads of anything that is not a document or data
#
# Writes are never filtered by extension: a file the agent *created* is
# always the agent's doing, whatever it is called.
NOT_THEIRS = (f"{os.sep}.venv{os.sep}", f"{os.sep}site-packages{os.sep}",
              f"{os.sep}__pycache__{os.sep}", f"{os.sep}.git{os.sep}",
              f"{os.sep}node_modules{os.sep}", f"{os.sep}.pytest_cache{os.sep}")
DOCUMENTS = (".md", ".txt", ".json", ".jsonl", ".csv", ".tsv", ".yaml",
             ".yml", ".toml", ".ini", ".xml", ".html")


class TurnLog:
    """The events of one customer turn, in the order they happened."""

    def __init__(self):
        self._lock = threading.Lock()
        self._events: list[dict] = []
        self._t0 = time.monotonic()

    def add(self, kind: str, title: str, note: str = "", body: str = "",
            diff: list | None = None, path: str | None = None) -> dict:
        event = {"k": kind, "t": title, "n": note,
                 "b": body[:MAX_BODY], "at": time.monotonic() - self._t0}
        if diff:
            event["diff"] = diff
        if path:
            event["_path"] = path
        with self._lock:
            self._events.append(event)
        return event

    def events(self) -> list[dict]:
        with self._lock:
            return [{k: v for k, v in e.items() if k != "_path"}
                    for e in self._events]

    def pending_file_events(self) -> list[dict]:
        with self._lock:
            return [e for e in self._events if e.get("_path")]

    def repeats(self, tag: str) -> bool:
        """Was the event just logged this same file, opened the same
        way? `open()` raises the audit event twice — once for the io
        call, once for the syscall under it — and one line per read is
        what the panel wants."""
        with self._lock:
            return bool(self._events) and self._events[-1].get("_path") == tag


CURRENT: TurnLog | None = None


@contextlib.contextmanager
def muted():
    """Nothing recorded in here is the agent's doing.

    Rendering a traceback opens the source file it points at, and
    reading a memory file to show it opens that — both would otherwise
    turn up in the panel as file reads the student never wrote.
    """
    global CURRENT
    saved, CURRENT = CURRENT, None
    try:
        yield
    finally:
        CURRENT = saved


def add(kind: str, title: str, note: str = "", body: str = "",
        diff: list | None = None, path: str | None = None):
    log = CURRENT
    if log is not None:
        return log.add(kind, title, note, body, diff, path)
    return None


# ── files: which ones the agent opened, and what for ──────────────────

_watching: dict = {}


def watch_files(agent_dir: pathlib.Path, memory_dir: pathlib.Path) -> None:
    """Log every file the agent opens under its own directory.

    An audit hook is process-wide and cannot be removed once installed,
    which is why it is installed by the server and never by the REPL,
    and why it does nothing at all while no turn is in flight. It records
    paths only — reading the file from inside a hook that fires on
    `open()` is a loop — and the bodies are filled in afterwards by
    `settle_file_events`.
    """
    installed = bool(_watching)
    _watching["dir"] = str(agent_dir.resolve())
    _watching["memory"] = str(memory_dir.resolve())
    if installed:  # a hook cannot be removed, so it is installed once
        return

    def hook(name, args):
        if name != "open" or CURRENT is None:
            return
        try:
            path, mode = args[0], args[1]
            flags = args[2] if len(args) > 2 else 0
        except (IndexError, TypeError):
            return
        if not isinstance(path, str) or not path:
            return
        # `io.open` reports the mode string; the `os.open` underneath it
        # reports permission bits and flags instead.
        wrote = (any(c in mode for c in "wax+") if isinstance(mode, str)
                 else bool((flags or 0) & (os.O_WRONLY | os.O_RDWR
                                           | os.O_CREAT | os.O_APPEND)))
        _note_open(os.path.abspath(path), wrote)

    sys.addaudithook(hook)


def _note_open(path: str, wrote: bool) -> None:
    root, memory = _watching["dir"], _watching["memory"]
    if not path.startswith(root + os.sep):
        return
    if any(part in path for part in NOT_THEIRS):
        return
    in_memory = path.startswith(memory + os.sep)
    inside_stall = f"{os.sep}.stall{os.sep}" in path
    if inside_stall and not in_memory:
        return  # our own bookkeeping, not the agent's
    if not wrote and not in_memory and not path.endswith(DOCUMENTS):
        return  # an import, not a read: see NOT_THEIRS
    rel = os.path.relpath(path, os.path.dirname(root))
    if in_memory:
        kind = "mem"
    elif "skill" in os.path.basename(path).lower() or \
            f"{os.sep}skills{os.sep}" in path:
        kind = "skill"
    else:
        kind = "file"
    verb = "wrote" if wrote else "read"
    tag = f"{verb}\t{path}"
    if CURRENT is not None and CURRENT.repeats(tag):
        return
    add(kind, f"{verb} {rel}", "", "", None, path=tag)


def settle_file_events(log: TurnLog) -> None:
    """Fill in size and, for small files, content — after the turn, when
    opening them is no longer re-entrant.

    Recording is off for the duration: reading a file to show it is our
    doing, not the agent's, and it would otherwise appear in the panel
    as a read the student never wrote.
    """
    with muted():
        _settle(log)


def _settle(log: TurnLog) -> None:
    for event in log.pending_file_events():
        verb, _, path = event.pop("_path").partition("\t")
        try:
            size = os.path.getsize(path)
        except OSError:
            event["n"] = "gone"
            continue
        event["n"] = f"{size:,} bytes"
        event["b"] = f"{path}\n  {verb} {size:,} bytes"
        if size <= 4096:
            try:
                event["b"] += "\n\n" + pathlib.Path(path).read_text()
            except (OSError, UnicodeDecodeError):
                pass


# ── print: the agent's own words, with the line that said them ────────

class PrintTap(io.TextIOBase):
    """stdout for the duration of a turn: still printed to the terminal,
    and also logged as an event tagged with the agent line that wrote
    it. The tag is a stack walk rather than anything the student has to
    opt into — `print("board says milo=1")` is how people debug, and it
    is worth showing beside the LLM calls it sits between."""

    def __init__(self, real, root: pathlib.Path):
        self._real = real
        self._root = str(root.resolve())
        self._buffer = ""

    def write(self, text: str) -> int:
        self._real.write(text)
        self._buffer += text
        while "\n" in self._buffer:
            line, _, self._buffer = self._buffer.partition("\n")
            if line.strip():
                add("print", line.strip()[:200], self._origin(), line)
        return len(text)

    def flush(self):
        self._real.flush()

    def close(self):
        if self._buffer.strip():
            add("print", self._buffer.strip()[:200], self._origin(),
                self._buffer)
        self._buffer = ""

    def _origin(self) -> str:
        frame = sys._getframe(1)
        while frame is not None:
            name = frame.f_code.co_filename
            if name.startswith(self._root + os.sep):
                return f"{os.path.basename(name)}:{frame.f_lineno}"
            frame = frame.f_back
        return ""


# ── bodies: request and response JSON, trimmed to something readable ──

def pretty(payload, limit: int = 1200) -> str:
    """JSON as the panel shows it: indented, with the long strings —
    an inlined menu, a whole conversation replayed — cut short rather
    than pushing everything after them off the screen."""
    try:
        data = json.loads(payload) if isinstance(payload, (bytes, str)) \
            else payload
    except (json.JSONDecodeError, UnicodeDecodeError):
        text = payload.decode(errors="replace") if isinstance(payload, bytes) \
            else str(payload)
        return text[:MAX_BODY]
    return json.dumps(_trim(data, limit), indent=2, ensure_ascii=False)


def _trim(node, limit: int):
    if isinstance(node, str) and len(node) > limit:
        return node[:limit] + f"\n... [{len(node) - limit:,} more characters]"
    if isinstance(node, dict):
        return {k: _trim(v, limit) for k, v in node.items()}
    if isinstance(node, list):
        return [_trim(v, limit) for v in node]
    return node
