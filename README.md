# Kopi Kaki ☕

You are about to run the counter of a Singapore hawker drinks stall.
Customers will talk to your agent; your agent writes down the order; the
stall prices it and keeps score. Two hours, five levels, one leaderboard.

**No agent frameworks, no vendor SDKs.** You get URLs, not clients.
Whatever your agent does — retrieval, tool calls, memory — you build it
yourself. Ordinary libraries are fine: `my-stall/pyproject.toml` is
yours, and anything you add there is installed for your graded run too.
Most people never touch it, and the standard library is enough.

## Setup

**Codespaces (recommended):** *Use this template → Create a new
repository* to get your own copy, then *Code → Create codespace*. When
it opens, give the stall your key — one line in the terminal:

```bash
echo 'LLM_API_KEY=paste-your-key-here' > .env
```

Then `stall selfcheck`. Done.

`.env` is gitignored, so your key never leaves the Codespace, and it
survives rebuilds and new terminals — which is why this beats
`export LLM_API_KEY=...`, where the key dies with the shell that set it.

**Local:** Python 3.11+, `git clone`, and set the environment below
(a `.env` file in the repo root also works). Install
[uv](https://docs.astral.sh/uv/) if you want to add libraries; without
it everything still works on the standard library.

| Variable | Meaning |
|---|---|
| `LLM_API_KEY` | your own API key (used for local runs only) |
| `LLM_BASE_URL` | OpenAI-compatible endpoint (default: the recommended provider from the pre-workshop email) |
| `LLM_MODEL` | model for local runs (graded runs use the stall's model — it is on the projector) |
| `STALL_URL` | the stall's address (the instructor will give you this) |
| `EMBEDDING_BASE_URL` | optional, for local embedding calls (e.g. dense retrieval) — see `docs/02-ground-it.md` |
| `EMBEDDING_MODEL` | optional, the embedding model to request; unset means embedding calls 502 locally |

Verify your key works:

```bash
stall selfcheck
```

## The loop

```bash
stall init                 # create my-stall/ with the agent scaffold
stall chat                 # talk to your own agent in a browser — YOU are the customer
stall fetch menu           # download the menu book into my-stall/
stall fetch promotions     # download the promotions poster into my-stall/
stall fetch solution --level 2   # stuck? the reference lands in reference/
stall submit               # graded run against the hidden customers
stall history              # list your past submissions and their token cost
```

`stall` is `bin/stall`; in Codespaces it is already on your PATH.
Otherwise use `python3 -m stall ...` from the repo root.

## The counter

`stall chat` serves a page on `http://127.0.0.1:7788` and opens it. You
type as the customer; your agent answers. Down the right of every reply
is **SEE INSIDE** — click it, or click your agent anywhere, and you get
what the terminal could never show you: every LLM request and response
in full, every stock call, every `print()` with the line that printed
it, every document it read and every file it wrote, and every time the
world moved under you. The order chit hangs under your agent, priced
at the stall's own till.

Two buttons. **NEW** starts a fresh customer on the same code — a
different face at the counter, drawn at random, and the same memory
directory it left behind.
**SUBMIT** sends a graded run up and follows it while its window is
open; close that window and keep talking, and press SUBMIT again to
pick the run back up.

**When you have edited `agent.py`, restart the server**: Ctrl-C, then
`stall chat` again. There is no reload button. A restart is the only
thing that gives you what a graded run gets — your new code, your
libraries resolved from `pyproject.toml`, and a conversation that
starts where the new code starts. It takes about a second, and your
memory directory survives it.

**Nothing else on the page moves unless you move it.** It does not poll,
it does not watch your files, and it does not redraw itself — so the
caret stays in your sentence and a panel you opened stays open. If
`stall chat` has stopped, the page says so the next time you ask it for
something, because that is when it matters.

The meter in the corner counts **tokens**, not money: the leaderboard
ranks on revenue and then on the token count itself, so the count is
the number you are judged by. The only price the page quotes is the one
the stall reports about a finished run.

### In Codespaces

Nothing extra to do. `stall chat` notices it is in a Codespace, forwards
port 7788, and prints — and opens — the `https://…app.github.dev`
address instead of `127.0.0.1`, which is the one your laptop can
actually reach. If no tab opens, the URL in the terminal and the **Ports**
panel both work.

| flag | |
|---|---|
| `--cli` | stay in the terminal: the same loop, without the panel |
| `--port N` | serve somewhere other than 7788 |
| `--no-browser` | serve the page but do not open it — print the URL and wait |
| `--dir` | your stall directory (default `my-stall`) |
| `--reset-memory` | wipe `.stall/memory/` before starting |

The stock board `stall chat` shows you is a **practice** board. It rolls
fresh for every conversation — **NEW** gives you a different one — and it
is not the board your graded run sees. It has the same shape: something
out of stock, something down to its last cup, and a walk-up customer
coming for that cup a turn or two in. Holds on it are real, so this is
where you rehearse Level 3 before it costs you a sale. Until the stall
reaches level 3 it is an ordinary day and nothing moves; when the stall
advances, hit **NEW** to get the board that does.

## Adding a library

`stall init` leaves a `pyproject.toml` beside your `agent.py`. Add what
you want to its `dependencies`, and `stall chat` will run your agent
against it — the local loop goes through `uv run`. The stall resolves
the same manifest when you submit, so local and graded agree.

A manifest the stall cannot resolve is a **structural error**: you get
uv's output in full, and it costs you no run and no cooldown, exactly
like a syntax error in `agent.py`. If a `uv.lock` is present the stall
installs exactly that, manifest edits included or not — `stall chat`
keeps the lock current for you, so this only bites if you hand-edit
`pyproject.toml` and never run the local loop again. Without a lock the
stall resolves fresh.

## The contract

Your submission is the `my-stall/` directory. It must contain `agent.py`
defining:

```python
class Agent:
    def __init__(self, config): ...
    def handle_turn(self, message: str) -> str: ...
    def current_order(self) -> dict: ...
```

The stall makes one `Agent` per conversation and speaks first. Your
`current_order()` returns `{"items": [{"name": str, "qty": int}]}` —
modifiers baked into the name, exactly as Singaporeans order
(`Kopi C Kosong Peng` is one item). Naming is resolved leniently: case,
punctuation, and word order never cost you a sale. The wrong drink does.

`config` hands you: `llm_base_url`, `llm_model`, `llm_api_key`,
`embedding_base_url`, `embedding_api_key`, `embedding_model`,
`stock_url`, `memory_dir`, `customer_id`.

## Scoring

Two numbers, never netted: **revenue** (correctly served orders) and
**token cost** (what your agent spent, charged even on lost orders — the
stall's gas and electricity). One leaderboard, ranked on revenue, cost
as tiebreaker. Best run counts.

Level briefs are in `docs/` — all five, from the start. Reading ahead is
allowed and always has been.

## Troubleshooting

1. RESOURCE_EXHAUSTED error while the agent is coding
- This means the model you've selected has reached one of its rate limits (for example, Tokens Per Minute). Below the chat interface, set the model beside the `Agent` icon to `Auto`.

2. My order is not taken in `stall chat`
- Make sure that LLM_API_KEY is set. You can run `echo $LLM_API_KEY` to check if it's set correctly.
- To help you debug what's going on, click the `See Inside` button at the bottom of each reply from the agent on the `stall chat` web chat interface.
