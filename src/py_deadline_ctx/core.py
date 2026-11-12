import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable, Iterator, Optional


class DeadlineExceeded(Exception):
    """Raised by :func:`check` when the active deadline has passed."""


def _default_clock() -> float:
    """Monotonic wall clock.

    ``time.monotonic()`` is used instead of ``time.time()`` because deadlines
    are durations, not points in civil time.  A system clock adjustment must
    not change whether a deadline has expired.
    """
    return time.monotonic()


# The active deadline, or None when no deadline has been installed.
_deadline: ContextVar[Optional[float]] = ContextVar("py_deadline_ctx_deadline", default=None)

# The clock used to create deadlines.  Kept as a module-level variable so the
# context manager can default it without forcing every caller to pass one.
_clock: Callable[[], float] = _default_clock


@contextmanager
def deadline(seconds: float, *, clock: Optional[Callable[[], float]] = None) -> Iterator[None]:
    """Install a deadline that lasts ``seconds`` from now.

    The deadline is stored in a :class:`contextvars.ContextVar`, so nested
    calls observe it without any argument threading.  On exit the previous
    deadline is restored, which means nested ``deadline`` blocks compose:
    the inner block shadows the outer one for its duration.

    ``seconds`` must be non-negative.  A value of ``0`` installs an already
    expired deadline, which is useful for testing and for "fail fast" paths.
    """
    if seconds < 0:
        raise ValueError("seconds must be non-negative")

    selected_clock = clock if clock is not None else _clock
    expires_at = selected_clock() + seconds
    token = _deadline.set(expires_at)
    try:
        yield
    finally:
        _deadline.reset(token)


def remaining(*, clock: Optional[Callable[[], float]] = None) -> Optional[float]:
    """Return seconds left before the active deadline, or ``None``.

    ``None`` means no deadline is installed.  A negative result means the
    deadline has already passed; callers that care should use :func:`check`
    instead of comparing the result themselves.
    """
    expires_at = _deadline.get()
    if expires_at is None:
        return None
    selected_clock = clock if clock is not None else _clock
    return expires_at - selected_clock()


def check(*, clock: Optional[Callable[[], float]] = None) -> None:
    """Raise :class:`DeadlineExceeded` if the active deadline has passed.

    This is a cooperative check.  It does not interrupt running code; callers
    invoke it at safe points.  When no deadline is installed it is a no-op.
    """
    left = remaining(clock=clock)
    if left is not None and left <= 0:
        raise DeadlineExceeded("deadline exceeded")
