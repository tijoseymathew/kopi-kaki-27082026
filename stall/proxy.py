"""Local metering proxy for `stall chat`.

The local loop points your agent's llm_base_url here; requests are
forwarded untouched to your real provider and the usage numbers are
counted on the way back — the same arrangement the stall uses during
graded runs, so the token column you see locally is the one you will be
charged.

A POST to `{llm_base_url}/embeddings` is forwarded the same way, to
EMBEDDING_BASE_URL instead of LLM_BASE_URL (see stall/config.py) — kept
separate rather than defaulting to the chat upstream, since there is no
guarantee the two live behind the same provider. Unset, it 502s instead
of guessing.

Sitting in the middle is also the only place that can show the chat UI
what your agent actually said to the model, so each round trip is
logged as a pair of events (request out, response back) when a turn is
being recorded. The REPL records nothing and the proxy behaves exactly
as it did.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import events


class MeterProxy:
    def __init__(self, upstream_base: str, embedding_base: str = "",
                 record: bool = False):
        self.upstream_base = upstream_base.rstrip("/")
        # No fallback to upstream_base: a request landing on /embeddings
        # with this unset means the student hasn't set EMBEDDING_BASE_URL
        # in .env, which is worth a clear 502 rather than a guess at
        # which provider it should have gone to.
        self.embedding_base = embedding_base.rstrip("/")
        self.total_tokens = 0
        self.calls = 0
        self.record = record
        self._lock = threading.Lock()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}/v1"

    def close(self):
        self._server.shutdown()

    def _count(self, tokens: int):
        with self._lock:
            self.total_tokens += tokens

    def _next_call(self) -> int:
        with self._lock:
            self.calls += 1
            return self.calls

    def _handler(proxy):
        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length)
                n = proxy._next_call() if proxy.record else 0
                if n:
                    events.add("llm", f"llm #{n}  \u2192  request",
                               _messages_note(body), events.pretty(body))
                started = time.monotonic()
                is_embedding = self.path.rstrip("/").endswith("/embeddings")
                if is_embedding and not proxy.embedding_base:
                    payload = json.dumps({
                        "error": "EMBEDDING_BASE_URL is not set \u2014 add it to .env"
                    }).encode()
                    status = 502
                else:
                    target = (f"{proxy.embedding_base}/embeddings" if is_embedding
                              else f"{proxy.upstream_base}/chat/completions")
                    req = urllib.request.Request(
                        target, data=body,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": self.headers.get("Authorization", ""),
                        })
                    try:
                        with urllib.request.urlopen(req, timeout=120) as resp:
                            payload, status = resp.read(), resp.status
                    except urllib.error.HTTPError as e:
                        payload, status = e.read(), e.code
                    except (urllib.error.URLError, TimeoutError) as e:
                        payload = json.dumps({"error": f"upstream unreachable: {e}"}).encode()
                        status = 502
                tokens = 0
                if status == 200:
                    try:
                        usage = json.loads(payload).get("usage") or {}
                        tokens = int(usage.get("total_tokens") or 0)
                        proxy._count(tokens)
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass
                if n:
                    seconds = time.monotonic() - started
                    events.add(
                        "llm", f"llm #{n}  \u2190  {_answer_note(payload)}",
                        f"{tokens:,} tok \u00b7 {seconds:.1f}s" if tokens
                        else f"{status} \u00b7 {seconds:.1f}s",
                        f"{status} {'OK' if status == 200 else ''}"
                        f"   {seconds:.1f}s\n" + events.pretty(payload))
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        return Handler


def _messages_note(body: bytes) -> str:
    """How much conversation this request is carrying. The number that
    grows every turn is the one worth putting in the margin."""
    try:
        data = json.loads(body)
        chars = sum(len(str(m.get("content") or "")) for m in data["messages"])
        return f"{len(data['messages'])} msgs \u00b7 ~{chars // 4:,} tok in"
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return ""


def _answer_note(payload: bytes) -> str:
    """`content`, or the tools it wants called — the one line of the
    response worth reading before opening it."""
    try:
        message = json.loads(payload)["choices"][0]["message"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return "response"
    calls = message.get("tool_calls") or []
    if calls:
        names = ", ".join(c.get("function", {}).get("name", "?") for c in calls)
        return f"tool_calls: {names}"
    return "content"
