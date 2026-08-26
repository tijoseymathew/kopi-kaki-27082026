"""The `stall` command."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import sys
import time
import urllib.request

from . import api, config, web

SCAFFOLD = pathlib.Path(__file__).resolve().parent / "scaffold"
IDENTITY = pathlib.Path(".stall-identity.json")


def cmd_init(args, env):
    target = pathlib.Path(args.dir)
    target.mkdir(parents=True, exist_ok=True)
    for src in SCAFFOLD.iterdir():
        dest = target / src.name
        if dest.exists() and not args.force:
            print(f"{dest} exists — skipped (use --force to overwrite)")
            continue
        shutil.copy(src, dest)
        print(f"wrote {dest}")
    print(f"\nYour stall lives in {target}/. Try: stall chat")


def cmd_fetch(args, env):
    if args.what in ("menu", "promotions"):
        text = api.get_text(f"{env['STALL_URL']}/{args.what}")
        dest = pathlib.Path(args.dir) / f"{args.what}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
        print(f"wrote {dest} ({len(text)} bytes)")
    elif args.what == "solution":
        if not args.level:
            sys.exit("which one? stall fetch solution --level 1|2|3")
        status, data = api.get_json_status(
            f"{env['STALL_URL']}/solution/{args.level}?code={_join_code(args)}")
        if status != 200:
            # The stall's own words: which level it is on, or that the
            # code did not check out. Nothing to add.
            sys.exit(data.get("error", data))
        dest = pathlib.Path("reference") / f"level{args.level}"
        dest.mkdir(parents=True, exist_ok=True)
        for name, content in data["files"].items():
            (dest / name).write_text(content)
            print(f"wrote {dest / name}")
        print("\nThe reference never touches your working directory. "
              "Read it, take what you need, rejoin the room.")
    else:
        sys.exit("stall fetch menu|promotions|solution")


UNDER_UV = "STALL_UNDER_UV"


def _reexec_under_uv(directory: str) -> None:
    """Re-run this command inside the stall's own uv environment.

    Does not return if it succeeds. The local loop imports agent.py into
    this process, so if the submission declares dependencies they have to
    be importable *here* — otherwise `stall chat` and the graded run
    would disagree about what exists. No manifest, or no uv on the box,
    and we carry on as before on the bare standard library.
    """
    if os.environ.get(UNDER_UV):
        return
    manifest = pathlib.Path(directory) / "pyproject.toml"
    if not manifest.exists():
        return
    uv = shutil.which("uv")
    if uv is None:
        print(f"note: {manifest} found, but uv is not installed — running on "
              "the standard library only", file=sys.stderr)
        return
    repo = str(pathlib.Path(__file__).resolve().parent.parent)
    child = dict(os.environ, **{UNDER_UV: "1"})
    child["PYTHONPATH"] = os.pathsep.join(
        [repo] + ([p] if (p := child.get("PYTHONPATH")) else []))
    os.execve(uv, [uv, "run", "--project", str(manifest.parent),
                   "python", "-m", "stall", *sys.argv[1:]], child)


def cmd_chat(args, env):
    """The local loop, in a browser tab — or in this terminal.

    The browser is the front door: it can show what the terminal cannot,
    which is what your agent did between the customer's message and its
    reply. `--cli` is the same loop with the same practice board, for a
    box with no browser, a slow tunnel, or a preference.
    """
    _reexec_under_uv(args.dir)
    if args.cli:
        from .repl import chat
        chat(args.dir, env, args.reset_memory)
        return
    web.serve(args.dir, env, args.reset_memory,
              port=args.port, open_browser=not args.no_browser)


def _join_code(args) -> str:
    """The code off the paper slip, remembered between commands."""
    ident = json.loads(IDENTITY.read_text()) if IDENTITY.exists() else {}
    code = getattr(args, "code", None) or ident.get("code")
    if not code:
        code = input("join code (on your paper slip): ").strip()
    ident["code"] = code
    IDENTITY.write_text(json.dumps(ident))
    return code


def _identity(args) -> dict:
    ident = {}
    if IDENTITY.exists():
        ident = json.loads(IDENTITY.read_text())
    if args.code:
        ident["code"] = args.code
    if getattr(args, "name", None):
        ident["name"] = args.name
    if not ident.get("code"):
        ident["code"] = input("join code (on your paper slip): ").strip()
    if not ident.get("name"):
        ident["name"] = input("name your stall (leaderboard name): ").strip()
    IDENTITY.write_text(json.dumps(ident))
    return ident


def _rename(ident: dict) -> dict:
    """Forget the name the stall refused and ask for another, now.

    Without this the ASCII and clash checks are a trap: `_identity`
    writes the name to the identity file *before* joining and only
    prompts when the key is absent, so re-running `stall submit` would
    replay the rejected name and be refused identically, forever,
    unless the student happened to know about --name.
    """
    ident.pop("name", None)
    IDENTITY.write_text(json.dumps(ident))
    try:
        ident["name"] = input("name your stall (leaderboard name): ").strip()
    except EOFError:
        sys.exit("no name given")
    IDENTITY.write_text(json.dumps(ident))
    return ident


def _join(env, ident: dict) -> str:
    """Join, re-prompting for as long as the stall refuses the name.
    Returns the name the stall *accepted*, which is not always the one
    typed — a student who names nothing is assigned one."""
    while True:
        status, out = api.post_json(
            f"{env['STALL_URL']}/join",
            {"code": ident["code"], "name": ident.get("name") or ""})
        if status == 200:
            # Remember what was accepted, so a student who wanted an
            # assigned name is not re-prompted on every submission.
            ident["name"] = out["stall"]
            IDENTITY.write_text(json.dumps(ident))
            return out["stall"]
        if status != 400:
            sys.exit(f"join failed: {out.get('error', out)}")
        # The stall's own words: non-ASCII, too long, or already
        # another stall's. Nothing to add.
        print(f"the stall refused that name: {out.get('error', out)}")
        ident = _rename(ident)


def cmd_submit(args, env):
    from .session import pack

    ident = _identity(args)
    directory = pathlib.Path(args.dir)
    # .toml/.lock carry the manifest; .venv is built at the stall, not sent
    files = pack(directory)
    if not files:
        sys.exit(f"nothing to submit in {directory}/")

    # The name the stall accepted, not the one typed locally: a student
    # who names nothing is assigned one, and it is what the projector
    # will show.
    stall_name = _join(env, ident)

    print(f"submitting {len(files)} file(s) as {stall_name!r}... "
          f"(this can take a while if the stall is busy grading)")
    # /submit blocks until this submission actually clears the stall's
    # admission queue, not just until it is accepted — GRADER_WORKERS=2
    # means that wait is bounded by whatever else is already grading, not
    # by anything under this client's control. The default 60s timeout is
    # sized for a quick request/response and will fire while the stall is
    # still legitimately working: the client then reports a connection
    # failure for a submission the stall may go on to accept anyway. 600s
    # comfortably covers the worst wait observed under real contention
    # (~320s) with margin, while still giving up on a truly hung stall.
    status, out = api.post_json(f"{env['STALL_URL']}/submit",
                                {"code": ident["code"], "files": files},
                                timeout=600)
    if status == 422:
        print("\nSTRUCTURAL ERROR (no run consumed, no cooldown):\n")
        print(out["structural_error"])
        sys.exit(1)
    if status != 200:
        sys.exit(f"rejected: {out.get('error', out)}")

    run_id = out["run_id"]
    print(f"run {run_id} queued. The 25 customers are walking up...")
    said = None
    while True:
        time.sleep(2)
        run = api.get_json(f"{env['STALL_URL']}/runs/{run_id}")
        if run["status"] in ("done", "failed"):
            break
        # Only when it changes: this loop ticks every two seconds and a
        # run is minutes long, so printing every poll buries the result
        # under a page of identical lines.
        line = _progress_line(run)
        if line != said:
            print(line)
            said = line
    if run["status"] == "failed":
        sys.exit(f"the stall broke, not you: {run.get('error')}")

    print(f"\n=== run {run_id} ===")
    _print_result(run)


# The five kinds of hidden customer, in the order the levels introduce
# them, and what to call each one out loud. The names are not a leak:
# cases.py says "8 baseline, 6 menu-dependent, 4 stock-dependent, 4
# combo-eligible, 3 returning regulars" in its own docstring, and the
# workshop brief says it too. What is hidden is which customer is which.
KIND_LABELS = [
    ("baseline", "baseline"),
    ("menu", "menu-dependent"),
    ("stock", "stock-dependent"),
    ("combo", "combo-eligible"),
    ("regular", "returning regulars"),
]

# Why a case was lost, worst-understood first: an order that never
# resolved is a different bug from one that resolved to the wrong thing,
# and both are different from an agent that fell over.
FAILURE_LABELS = [
    ("unresolvable_item", "ordered something off no menu"),
    ("wrong_qty_items", "wrong items or quantities"),
    ("stock_mismatch", "right order, not servable at settlement"),
    ("crashed", "your agent raised"),
    ("timed_out", "your agent hung"),
]

HALT_REASONS = {
    "token_ceiling": "at the token ceiling",
    "run_deadline": "at the run deadline",
    "respawns_exhausted": "respawns exhausted (harness kept crashing/hanging)",
}


def _progress_line(run: dict) -> str:
    """One line for a run that is still going.

    The stall publishes a case counter that moves every case and a
    revenue total that moves every fifth, so the two disagree on purpose
    — `through` says which case the money is counted to, and this says
    so out loud rather than letting the smaller number look like a bug.
    """
    p = run.get("progress")
    if not p:
        return f"  ...{run['status']}"
    parts = [f"  ...{p['done']}/{p.get('total') or 25} served"]
    if p.get("through"):
        parts.append(f"${p['revenue_cents'] / 100:.2f} through {p['through']}")
    if run.get("tokens"):
        parts.append(f"{run['tokens']:,} tokens")
    return "   ".join(parts)


def _print_result(run: dict) -> None:
    """The whole of what a graded run says back.

    Everything printed here is decided at the stall — which categories
    are in `by_kind` is the level window, and the two operational counts
    are absent rather than zero. Nothing in this function chooses what a
    student may see; it chooses how to say it.
    """
    print(f"revenue     ${run['revenue_cents'] / 100:.2f}   "
          f"({run['sales']} sales, {run['lost']} lost)")
    print(f"token cost  ${run['token_cost_cents'] / 100:.2f}   "
          f"({run['tokens']:,} tokens)")

    by_kind = run.get("by_kind") or {}
    if by_kind:
        # Windowed to the level this run was submitted at, and
        # cumulative — so a regression in an earlier level's cases is
        # visible here and not hidden behind the newest kind.
        print(f"\nby category (through Level {run.get('level', 1)}):")
        for kind, label in KIND_LABELS:
            counts = by_kind.get(kind)
            if counts:
                print(f"  {label:<22} {counts['sales']}/{counts['total']}")

    reasons = run.get("failure_reasons") or {}
    if reasons:
        # Unwindowed on purpose, and labeled apart from the block above
        # so the two are never read as one set of numbers that ought to
        # agree: a crash a future level's case triggers counts here.
        print("\nlost cases, across your whole run:")
        for reason, label in FAILURE_LABELS:
            if reasons.get(reason):
                print(f"  {label:<40} {reasons[reason]:>2}")

    # The three operational signals, together and set off from the
    # numbers above: they are about the run rather than about the agent,
    # and two of them are absent on almost every run.
    notes = []
    if run["halted"]:
        why = HALT_REASONS.get(run.get("halt_reason"), "early")
        notes.append(f"run HALTED {why} — scored on what it earned")
    # "before recovering" is only true if it did. When the budget is what
    # stopped the run, the halt line above has already said so, and a
    # count of 4 out of 3 underneath it would only contradict it.
    if run.get("respawns") and run.get("halt_reason") != "respawns_exhausted":
        notes.append(f"the harness respawned {run['respawns']} of 3 times "
                     f"before recovering")
    if run.get("upstream_errors"):
        notes.append(f"upstream LLM errors: {run['upstream_errors']} "
                     f"(not your fault — the provider had trouble, "
                     f"not your agent)")
    if notes:
        print()
        for note in notes:
            print(note)

    print("\nNo per-case feedback — the customers are hidden. "
          "Imagine harder, iterate, resubmit.")


def _history_line(number: int, run: dict) -> str:
    """One line for one past submission — a history is only useful if
    it stays scannable across a session's worth of runs, so this says
    no more than status, revenue, and tokens."""
    status = run["status"]
    if status in ("queued", "running"):
        return f"run {number:03d}  {status:<8} {run['tokens']:,} tokens so far"
    if status == "failed":
        return f"run {number:03d}  failed   the stall's bug, not yours"
    line = (f"run {number:03d}  done     "
            f"${run['revenue_cents'] / 100:.2f} revenue "
            f"({run['sales']} sales, {run['lost']} lost)   "
            f"{run['tokens']:,} tokens (${run['token_cost_cents'] / 100:.2f})")
    if run["halted"]:
        line += "   HALTED"
    if run.get("is_best"):
        line += "   ← your leaderboard entry"
    return line


def cmd_history(args, env):
    code = _join_code(args)
    status, out = api.post_json(f"{env['STALL_URL']}/runs/mine", {"code": code})
    if status != 200:
        sys.exit(f"could not fetch your history: {out.get('error', out)}")
    runs = out["runs"]
    if not runs:
        print("no submissions yet — `stall submit` when you're ready.")
        return
    print(f"{len(runs)} submission(s):\n")
    for number, run in enumerate(runs, 1):
        print(_history_line(number, run))


def cmd_selfcheck(args, env):
    if not env.get("LLM_API_KEY"):
        sys.exit("LLM_API_KEY is not set")
    req = urllib.request.Request(
        env["LLM_BASE_URL"] + "/chat/completions",
        data=json.dumps({"model": env["LLM_MODEL"],
                         "messages": [{"role": "user", "content": "Say OK"}],
                         "max_tokens": 10}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + env["LLM_API_KEY"]})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    print(f"key works — {env['LLM_MODEL']} replied: "
          f"{data['choices'][0]['message']['content']!r}")
    try:
        state = api.get_json(f"{env['STALL_URL']}/state")
        print(f"stall reachable — level {state['level']}, "
              f"graded model {state['model']}")
    except api.StallError as e:
        print(f"stall not reachable yet ({e}) — fine before the workshop starts")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="stall", description="Kopi Kaki workshop CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="create your working directory from the scaffold")
    p.add_argument("--dir", default="my-stall")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("fetch", help="download menu / promotions / a reference solution")
    p.add_argument("what", choices=["menu", "promotions", "solution"])
    p.add_argument("--level", type=int, choices=[1, 2, 3])
    p.add_argument("--dir", default="my-stall")
    p.add_argument("--code", help="your join code (references need it)")
    p.set_defaults(fn=cmd_fetch)

    p = sub.add_parser("chat", help="talk to your own agent — you play the customer")
    p.add_argument("--dir", default="my-stall")
    p.add_argument("--reset-memory", action="store_true")
    p.add_argument("--cli", action="store_true",
                   help="stay in the terminal instead of opening a browser")
    p.add_argument("--port", type=int, default=web.DEFAULT_PORT,
                   help=f"port for the local chat server (default {web.DEFAULT_PORT})")
    p.add_argument("--no-browser", action="store_true",
                   help="serve the page but do not open it")
    p.set_defaults(fn=cmd_chat)

    p = sub.add_parser("submit", help="graded run against the hidden customers")
    p.add_argument("--dir", default="my-stall")
    p.add_argument("--code", help="your join code")
    p.add_argument("--name", help="your stall's leaderboard name")
    p.set_defaults(fn=cmd_submit)

    p = sub.add_parser("history", help="list your past submissions")
    p.add_argument("--code", help="your join code")
    p.set_defaults(fn=cmd_history)

    p = sub.add_parser("selfcheck", help="verify your key and the stall address")
    p.set_defaults(fn=cmd_selfcheck)

    args = parser.parse_args(argv)
    env = config.load()
    try:
        args.fn(args, env)
    except api.StallError as e:
        sys.exit(str(e))
