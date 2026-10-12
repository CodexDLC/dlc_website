"""Расчёт длительности в целых минутах без ошибок дробных часов."""

from django.utils.translation import gettext as _

from features.reporting.time import duration_minutes  # noqa: F401


def format_minutes(minutes):
    hours, remainder = divmod(minutes, 60)
    return _("%(hours)d ч %(minutes)02d мин") % {"hours": hours, "minutes": remainder}
