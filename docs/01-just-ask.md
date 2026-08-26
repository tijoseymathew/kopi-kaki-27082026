# Level 1 — Just Ask

## The lost sale

Your scaffold agent met its first customer this morning:

> **Customer:** One kopi, thanks.
>
> **Your agent:** Sorry ah, still setting up the stall.

```
resolved order: (empty)          till total: $0.00     SALE LOST
```

The customer wanted the single most-ordered drink in Singapore, said so
plainly, and walked away with nothing. The stall earned $0.00 and you
still paid for zero tokens — the only number that will ever be this
good again.

## The capability

Make the agent listen. One HTTP call per turn to an OpenAI-compatible
endpoint — `POST {llm_base_url}/chat/completions`, no vendor SDK and no
agent framework — carrying the conversation so far and instructions to
do two things at once:

1. **Say something back.** One short sentence. On a single-turn customer
   a clarifying question *is* a lost sale — they are already gone.
   Commit to a reasonable reading.
2. **Write the order down, structured.** Get the model to hand back the
   full order in a shape you can parse — JSON is the obvious choice —
   and keep the parsed result in an instance attribute so
   `current_order()` can return it: `{"items": [{"name": ..., "qty": ...}]}`.

Models do not always return clean JSON. Decide what happens when
parsing fails — keeping the previous order beats crashing, because an
exception scores the whole conversation zero.

Test in `stall chat`. You play the customer: order plainly, order two
things, change your mind mid-sentence, watch the chit in the corner
price what your agent wrote down. When the reply is not what you
expected, click it — the panel behind it holds the exact request your
agent sent and the exact answer it got back, which is where nearly
every Level 1 bug turns out to be. When it stops embarrassing you,
`stall submit`.

You will not win every customer. Watch which dollars you leave on the
table — that is the syllabus for the next hour and a half.
