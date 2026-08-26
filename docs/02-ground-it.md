# Level 2 — Ground It

## The lost sale

A customer leaned on the counter and said:

> **Customer:** My colleague say you all famous for the kopi-milo mix
> thing. One of that.
>
> **Your agent:** One Kopi Milo for you!

```
resolved order: ✗ 'Kopi Milo'    UNRESOLVED — the stall sells no such drink
till total: $0.00                SALE LOST
```

The drink exists. It is called **Kopi Champion**, it costs $3.00, and it
is on page two of the menu book — a house special this stall invented,
which no model has ever seen in training. Your agent, asked about a
drink it didn't know, invented a plausible name. The till does not
accept plausible.

## The capability

Ground the agent in a document you own. `stall fetch menu` drops
`menu.md` into your working directory; it is yours now — edit it,
restructure it, annotate it.

The lazy move is to paste the whole book into every request. It works,
and it shows up on the scoreboard: the book is long, you pay for it
*every turn of every conversation*, and most of it is about drinks this
customer never mentioned. That is the second column climbing for no
revenue.

The better move is retrieval: send only what this conversation needs.
You own the file — split it, index it, keyword-match it, whatever you
can build in plain Python. Two things must always survive the cut:
the ordering grammar (how modifiers combine) and whatever section
mentions the words this customer actually used.

Now the descriptive orders land too — "coffee with evaporated milk,
less sweet" has an exact name in the book, and the book, not the
model's memory of the internet, is what your agent should trust.
