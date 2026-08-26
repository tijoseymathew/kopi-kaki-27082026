# Level 4 — Package It

## The lost sale

A father walked up with money he was ready to spend:

> **Customer:** Two milo dinosaur for my two boys.
>
> **Your agent:** Two Milo Dinosaur, coming right up!

```
resolved order: ✓ 2 × Milo Dinosaur   till total: $7.00   SALE MADE
```

A sale — and still a loss. The poster on the pillar says a third
Dinosaur would have been **half price**, the father had two boys and
himself, and the till would have rung **$8.75** if anyone had mentioned
it. He would have said yes. Nobody asked. Meanwhile, on the cost
column: if you have been pasting documents into every request since L2,
you are paying rent on paragraphs about a 1979 grand opening.

## The capability

`stall fetch promotions` gets you the poster. It is long, most of it is
irrelevant to any given order, and half the promotions on it are
expired. Do **not** ship it to the model raw — and do not paste a
summary into every prompt either. Package it as a **skill**.

A skill is a folder holding a `SKILL.md`, and the file opens with a few
lines of front-matter:

```
---
name: promotions
description: The two live promos, exact conditions, and the line to say.
  Read this before finalising any order of two or more drinks, or when
  anyone mentions a deal.
---
The Dino Deal: three or more from the Dinosaur family...
```

The trick — the entire trick — is that the model never sees the body by
default. At startup your agent scans `skills/*/SKILL.md` and puts only
the front-matter into the system prompt: a shelf of labelled folders, a
few tokens each. Then give the model one more action in your loop —
`{"action": "read_skill", "name": ...}` — and it pulls down the full
body only when the label says it is worth opening. You built this exact
loop at Level 3. The bookshelf is just one more thing your agent's
hands can reach.

This is progressive disclosure, and the packaging is not our invention:
a folder with a `SKILL.md`, front-matter naming it and promising when
it is useful, is the format agent skills ship in out in the world.
Author one here and you will recognise them everywhere.

You write both halves, and each is graded by a different column. The
body earns revenue: the two live promotions, their exact conditions,
one line each on when to offer. The description spends tokens — it is a
promise about when the body is worth reading, and a vague promise means
the model opens the folder for every single teh. Distil hard on both.

If it earns its keep, nothing stops you writing a second skill — the
ordering-lingo cheat sheet you have been carrying in the prompt since
L2 is a strong candidate. Two folders on the shelf, and a model that
opens the right one at the right time, is this level working: revenue
*up*, cost *down*, in the same run.

There is no reference solution from here on.
