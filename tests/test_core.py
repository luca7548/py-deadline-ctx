import unittest

from py_deadline_ctx import DeadlineExceeded, check, deadline, remaining


class FakeClock:
    """A deterministic clock the tests advance by hand.

    Deadlines are durations, so the tests never read the real clock; a fake
    clock keeps every assertion reproducible regardless of machine speed.
    """

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class DeadlineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()

    def test_no_deadline_installed(self) -> None:
        self.assertIsNone(remaining(clock=self.clock))
        # check() with no deadline must not raise.
        check(clock=self.clock)

    def test_remaining_counts_down(self) -> None:
        with deadline(30, clock=self.clock):
            self.assertEqual(remaining(clock=self.clock), 30)
            self.clock.advance(10)
            self.assertEqual(remaining(clock=self.clock), 20)

    def test_check_raises_after_expiry(self) -> None:
        with deadline(5, clock=self.clock):
            self.clock.advance(5)
            with self.assertRaises(DeadlineExceeded):
                check(clock=self.clock)

    def test_check_does_not_raise_before_expiry(self) -> None:
        with deadline(5, clock=self.clock):
            self.clock.advance(4.999)
            check(clock=self.clock)  # must not raise

    def test_zero_second_deadline_is_already_expired(self) -> None:
        with deadline(0, clock=self.clock):
            with self.assertRaises(DeadlineExceeded):
                check(clock=self.clock)

    def test_negative_seconds_rejected(self) -> None:
        with self.assertRaises(ValueError):
            with deadline(-1, clock=self.clock):
                pass

    def test_nested_deadline_shadows_outer(self) -> None:
        with deadline(100, clock=self.clock):
            self.clock.advance(10)
            with deadline(5, clock=self.clock):
                self.assertEqual(remaining(clock=self.clock), 5)
                self.clock.advance(5)
                with self.assertRaises(DeadlineExceeded):
                    check(clock=self.clock)
            # Inner block restored the outer deadline; 85 seconds remain
            # because the clock advanced 15 seconds in total.
            self.assertEqual(remaining(clock=self.clock), 85)

    def test_deadline_restored_after_exception(self) -> None:
        with deadline(10, clock=self.clock):
            try:
                with deadline(1, clock=self.clock):
                    raise RuntimeError("boom")
            except RuntimeError:
                pass
            self.assertEqual(remaining(clock=self.clock), 10)

    def test_deadline_cleared_after_exit(self) -> None:
        with deadline(10, clock=self.clock):
            pass
        self.assertIsNone(remaining(clock=self.clock))

    def test_default_clock_used_when_omitted(self) -> None:
        # No fake clock: exercise the real monotonic clock path.  We only
        # assert that a deadline is installed, not any particular value.
        with deadline(60):
            left = remaining()
            self.assertIsNotNone(left)
            self.assertGreater(left, 0)
            self.assertLessEqual(left, 60)


if __name__ == "__main__":
    unittest.main()
