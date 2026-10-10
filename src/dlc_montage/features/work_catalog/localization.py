"""Пакетное чтение названий из БД; исходные отчёты и ключи не меняются."""

import re
from dataclasses import replace

from django.utils.translation import get_language

from .models import CableRoute, CableType, WorkDescriptionTranslation, WorkType


class WorkNameResolver:
    """Один набор DB-переводов на проекцию, без запросов на каждую строку."""

    def __init__(self):
        self.names = {}
        for model in (WorkType, CableRoute, CableType):
            for de, ru in model.objects.values_list("name_de", "name_ru"):
                self.names[de] = (de, ru or de)
        for original, de, ru in WorkDescriptionTranslation.objects.values_list("original", "name_de", "name_ru"):
            self.names[original] = (de, ru)
        keys = sorted((key for key in self.names if key), key=len, reverse=True)
        self.pattern = (
            re.compile(r"(?<!\w)(?:" + "|".join(re.escape(key) for key in keys) + r")(?!\w)") if keys else None
        )

    def pair(self, original):
        text = str(original or "")
        if text in self.names:
            return self.names[text]
        if not self.pattern:
            return text, text
        return tuple(
            self.pattern.sub(lambda match, index=index: self.names[match.group()][index], text) for index in (0, 1)
        )

    def display(self, original):
        return self.pair(original)[0 if not (get_language() or "").startswith("ru") else 1]

    def rows(self, rows):
        return tuple(
            replace(
                row, name=self.display(row.name), route=self.display(row.route), cable_type=self.display(row.cable_type)
            )
            for row in rows
        )

    def snapshot_row(self, row):
        result = dict(row)
        for field in ("name", "route", "cable_type"):
            index = 1 if (get_language() or "").startswith("ru") else 0
            pair = (row.get(field + "_de"), row.get(field + "_ru"))
            result[field] = pair[index] or self.display(row.get(field, ""))
        return result
