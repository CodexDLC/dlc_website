"""Расчёт длительности в целых минутах без ошибок дробных часов."""

from datetime import datetime

from django.utils.translation import gettext as _


def duration_minutes(starts_at, ends_at):
    return int(
        (
            datetime.combine(datetime.min.date(), ends_at) - datetime.combine(datetime.min.date(), starts_at)
        ).total_seconds()
        // 60
    )


def format_minutes(minutes):
    hours, remainder = divmod(minutes, 60)
    return _("%(hours)d ч %(minutes)02d мин") % {"hours": hours, "minutes": remainder}
