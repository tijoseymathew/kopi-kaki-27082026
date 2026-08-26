"""Serve one submission over a unix socket.

    python3 <this file> <submission_dir> <socket_path>

Started by the grading script once per run and killed at the end of it.
It is deliberately invoked by path rather than with `-m`: that puts this
directory on `sys.path[0]` instead of the package above it, so the
submission's namespace holds these three files and not the stall's —
`cases.py` included. The import below is written for both, because the
client's copy of this directory is a package there.

Three things `socketserver` will not do for a unix socket, all of them
handled at bind:

  * it does not unlink a predecessor's inode, so `bind()` fails
    EADDRINUSE after a crash rather than replacing a socket nothing is
    listening on;
  * the inode is created at the process umask, and this one wants 0600;
  * `accept()` on AF_UNIX gives an empty peer address, where
    `BaseHTTPRequestHandler` expects a `(host, port)` pair and indexes
    into it.

SIGTERM is caught so an ordinary kill runs `server_close` and the socket
does not outlive the process. SIGKILL does not, which is why the unlink
at bind exists.
"""

from __future__ import annotations

import os
import signal
import socketserver
import sys

try:                       # a package, in the client's copy
    from .core import Host, make_handler
except ImportError:        # a directory on sys.path, run by path here
    from core import Host, make_handler


class HarnessServer(socketserver.ThreadingUnixStreamServer):
    """A threading HTTP server on a pathname unix socket.

    Threading because a submission may hold a request open while
    something else of ours has to be answered — `/health` during a
    hanging `/turn`, most of all, which is how the grader tells a wedged
    agent from a wedged harness.
    """

    daemon_threads = True

    def server_bind(self):
        try:
            os.unlink(self.server_address)
        except FileNotFoundError:
            pass
        super().server_bind()
        os.chmod(self.server_address, 0o600)

    def server_close(self):
        super().server_close()
        try:
            os.unlink(self.server_address)
        except OSError:
            pass

    def get_request(self):
        conn, _empty = super().get_request()
        return conn, ("unix", 0)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: __main__.py <submission_dir> <socket_path>",
              file=sys.stderr)
        return 2
    submission_dir, socket_path = argv

    server = HarnessServer(socket_path, make_handler(Host(submission_dir)))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
