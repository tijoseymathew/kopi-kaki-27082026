# Level 3 — Hold It

## The lost sale — twice

Mid-morning, a customer hedged their bet:

> **Customer:** Milo peng. If milo finish already, then teh c peng also can.
>
> **Your agent:** One Milo Peng coming up!

```
resolved order: ✓ 'Milo Peng'    1 × Milo Peng   $2.50   [SOLD OUT]
till total: —                    SALE LOST
```

The Milo ran out two customers ago. The customer *told you* what to do
about it, your menu book is fully up to date, and it did not help —
because stock is not in any document. It changes while you are standing
there.

Ten minutes later, a worse one. A mother asked whether there was still
bandung. Suppose your agent had checked the board — there was exactly
**one cup left** — and answered honestly: "Yes, got!" She ordered it,
then spent two turns messaging her daughter about ice. On "confirm ah",
the till said:

```
resolved order: ✓ 'Bandung'  1 × Bandung  $1.80  [GONE — 1 left at turn 1]
                ✓ 'Kopi'     1 × Kopi     $1.60
till total: $0.00                SALE LOST
```

While she was texting, the uncle sold that last cup to a walk-up at the
other end of the counter. Your agent checked. The answer was true. The
sale died anyway — because between knowing and paying, the world moved.
**Knowing is not holding.**

## The capability

Give the agent a hand that reaches into the world. `config["stock_url"]`
speaks both directions:

- **GET** returns the live board: every item, and how many cups are
  left right now.
- **POST** `{"name": ..., "qty": ...}` puts cups **on hold** for the
  customer at your counter. Held cups cannot be sold to anyone else,
  and they are still yours at settlement. The reply says whether it
  landed: `{"held": true, ...}` or `{"held": false, "reason": ...}`.

Wire both into a tool loop, which you will build yourself in vanilla
Python:

- Tell the model, in the system prompt, that the board exists and how
  to ask for things — distinct, parseable reply shapes
  (`{"action": "check_stock"}`, `{"action": "hold", "name": ..., "qty": ...}`
  against `{"reply": ..., "order": ...}`).
- When the model asks, do the HTTP call, append the result to the
  conversation, and call the model again.
- Cap the loop. A model that checks stock five times for one teh peng
  is spending your gas money.

## Rehearsing it

`stall chat` gives you a board to practise on. It is a **practice**
board, not the graded one: it rolls fresh for every conversation, so
**NEW** deals you a different day, and none of its numbers tell you
anything about the 25 hidden customers. What it does share is the
shape — one supply out, one drink down to its last cup, and a walk-up
coming for that cup a turn or two in.

So the whole loop is rehearsable before it costs you anything. Check
the board, find the row reading 1, hold it, keep the customer talking,
and watch the till preview keep pricing it. Then do it again without
the hold, and watch the walk-up take it: the panel shows the row
falling to 0 between your turns, and `sold out` appears on the chit
beside the drink you already promised. The clock moves on **your** turns, not on the wall and not
on your GETs — which is exactly how the graded board works, and why an
agent that never looks still loses the cup.

Two judgement calls, and they are different in kind. *When to look* is
about staleness — a customer saying "if finish" is a strong hint, and a
look costs only tokens. *When to act* is about the world — a hold takes
real cups off a real shelf, so take it the moment intent is clear and
stock is short, and don't hold what nobody asked for. Reading tells you
the truth; only acting keeps it true.
