"""Duration calculation shared by reporting adapters."""

from datetime import datetime


def duration_minutes(starts_at, ends_at):
    return int(
        (
            datetime.combine(datetime.min.date(), ends_at) - datetime.combine(datetime.min.date(), starts_at)
        ).total_seconds()
        // 60
    )
