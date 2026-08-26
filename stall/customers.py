"""Who is at the counter while you practise.

A graded run walks 25 hidden customers past the stall, and some of them
come back. Practice had exactly one, `local-regular`, for as long as the
server stayed up — and memory keyed on an id that never changes is a
memory that is never asked to recall anybody. Level 5 passed locally
whatever you wrote.

So the counter has a handful of regulars, and one is drawn at random
when `stall chat` starts and again on every fresh conversation — the
one who just left included, because a repeat draw is the case where
"the usual" has to work. The id is all your agent gets; the page draws
her a face to go with it.
"""

from __future__ import annotations

import random

LOCALS = ["mei", "siti", "priya", "joyce", "hui-en", "auntie-tan"]


def draw() -> str:
    """The next customer to walk up."""
    return random.choice(LOCALS)
