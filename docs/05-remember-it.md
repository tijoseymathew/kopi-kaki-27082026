# Level 5 — Remember It

## The lost sale

She was here this morning. Case 4. Kopi siew dai, "same order every
morning, ok?" — and your agent served her perfectly. She came back
after lunch:

> **Customer:** Morning! The usual ah.
>
> **Your agent:** Of course! What would you like today?

```
resolved order: (empty)          till total: $0.00     SALE LOST
```

She told you she was a regular. She told you the order. Your agent
wrote it on air. Three customers this afternoon will say "the usual" —
that is $8.10 of guaranteed revenue for anyone who wrote anything down.

## The capability

`config["memory_dir"]` is a writable directory that survives across
conversations within a run (it is wiped between runs — every graded run
starts with an empty shelf). `config["customer_id"]` tells you who is
at the counter; the loyalty QR did the entity resolution for you.

What to store and what to recall is the entire design space, and it is
yours: JSON per customer, one markdown notebook, whatever you can read
back fast. The trade is real on both columns —

- Store too little and "the usual" fails: lost revenue.
- Store too much — say, full transcripts you replay into every prompt —
  and the cost column balloons for customers who never come back.

A regular's second visit should be your *cheapest* conversation of the
day: read the file, book the order, one short LLM call, done. If your
memory makes returning customers more expensive, it is a diary, not a
memory.

Write on every conversation, or only when someone claims to be a
regular? Recall for everyone, or only when the words "usual" or "same"
appear? Your call. The three regulars will not announce themselves in
advance — and neither did the ones this morning.

## Practising it

`stall chat` draws one of the regulars at the counter when it starts,
and draws again every time you press **+ NEW** — which is why the id
under the customer changes and the memory directory does not. Sooner or
later the draw repeats: that conversation is the test. Serve her, press
**+ NEW** until she is back, and say "the usual" — whatever your agent
wrote down is all it has.
