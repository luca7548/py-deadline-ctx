"""Public API for py-deadline-ctx.

This package propagates a deadline through nested synchronous calls without
a framework.  The public surface is deliberately small: a context manager
that installs a deadline, a function that reads the current deadline, and a
function that raises when the deadline has passed.
"""

from .core import DeadlineExceeded, deadline, remaining, check

__all__ = ["DeadlineExceeded", "deadline", "remaining", "check"]
