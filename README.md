# py-deadline-ctx

Propagate a deadline through nested synchronous calls without a framework.

```python
from py_deadline_ctx import deadline, remaining, check


def fetch_row(row_id):
    check()  # raise DeadlineExceeded if the budget is gone
    return {"id": row_id}


with deadline(2.0):
    for row_id in (1, 2, 3):
        row = fetch_row(row_id)
        print(row, remaining())
```

## Why this exists

Passing a deadline as an extra argument through every function is noisy, and
threading it through a framework is heavier than most call graphs need.  This
library stores the deadline in a `contextvars.ContextVar`, so nested calls
read it with `remaining()` and `check()` without changing their signatures.

The trade-off is that a deadline is cooperative: `check()` only raises at the
points you call it.  It will not interrupt a long-running C call or a blocking
socket read.  That is intentional — the alternative is signals or threads,
which bring their own failure modes into code that merely wanted a budget.

One context manager, one reader, one checker:

- `deadline(seconds, *, clock=None)` — install a deadline lasting `seconds`.
- `remaining(*, clock=None)` — seconds left, or `None` if no deadline is set.
- `check(*, clock=None)` — raise `DeadlineExceeded` once the deadline passes.

## The awkward edge

Nested `deadline` blocks shadow rather than combine.  The inner block replaces
the outer deadline for its duration and restores it on exit, even if the inner
block raises.  If you want the shorter of two budgets, compute it yourself and
pass a single value.  `remaining()` returns a negative number after expiry;
use `check()` if you want the raise instead of the number.

All three functions accept a `clock` keyword.  It exists so tests can pass a
fake clock and so callers with a different monotonic source can supply one;
the default is `time.monotonic`.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

