from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    """Protocol for abstracting the current time source, allowing deterministic testing."""
    def now(self) -> datetime:
        ...


class SystemClock:
    """Standard system clock returning timezone-aware UTC datetime."""
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class MockClock:
    """Mock clock for deterministic testing, allowing time to be set and advanced."""
    def __init__(self, initial_time: datetime | None = None):
        if initial_time is not None:
            if initial_time.tzinfo is None:
                self._current_time = initial_time.replace(tzinfo=timezone.utc)
            else:
                self._current_time = initial_time.astimezone(timezone.utc)
        else:
            self._current_time = datetime.now(timezone.utc)

    def now(self) -> datetime:
        return self._current_time

    def set_time(self, new_time: datetime) -> None:
        if new_time.tzinfo is None:
            self._current_time = new_time.replace(tzinfo=timezone.utc)
        else:
            self._current_time = new_time.astimezone(timezone.utc)

    def advance(self, **kwargs) -> datetime:
        from datetime import timedelta
        self._current_time += timedelta(**kwargs)
        return self._current_time
