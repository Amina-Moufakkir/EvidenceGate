from __future__ import annotations

from dataclasses import dataclass
from datetime import date


class Clock:
    def today_iso(self) -> str:
        return date.today().isoformat()


@dataclass(frozen=True)
class FixedClock(Clock):
    today: str

    def today_iso(self) -> str:
        return self.today
