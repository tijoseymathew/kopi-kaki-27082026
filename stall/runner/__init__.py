"""The harness that hosts a student submission.

`core` is the shared half — the one implementation of "run a turn
against a student's Agent", copied verbatim into the client so that a
submission graded here and a submission driven by `stall chat` are
driven by the same code. `__main__` is the server half: a unix socket,
and the process the grader spawns once per run.

Nothing in this package knows about cases, worlds, tokens or venvs, and
nothing in it imports the rest of `kakistall`. That is what makes the
copy possible.
"""
