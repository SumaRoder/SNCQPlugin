from __future__ import annotations

from datetime import datetime
from dateutil.relativedelta import relativedelta


def format_duration_precise(start: datetime, end: datetime) -> str:
    if end < start:
        start, end = end, start

    rd = relativedelta(end, start)

    parts: list[str] = []
    if rd.years:
        parts.append(f"{rd.years}y")
    if rd.months:
        parts.append(f"{rd.months}M")
    if rd.days:
        parts.append(f"{rd.days}d")
    if rd.hours:
        parts.append(f"{rd.hours}h")
    if rd.minutes:
        parts.append(f"{rd.minutes}m")
    if rd.seconds:
        parts.append(f"{rd.seconds}s")

    return "".join(parts) if parts else "0s"
