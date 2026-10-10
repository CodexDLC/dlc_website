"""Двуязычный справочник работ."""

from typing import ClassVar

from django.db import models
from django.utils.translation import get_language, gettext_noop
from django.utils.translation import gettext_lazy as _


class WorkTypeQuerySet(models.QuerySet):
    def for_direction(self, direction):
        if direction not in ("ac", "dc"):
            raise ValueError("Direction must be 'ac' or 'dc'.")
        return self.filter(direction__in=(direction, "both"))


class WorkType(models.Model):
    class Direction(models.TextChoices):
        AC = "ac", "AC"
        DC = "dc", "DC"
        BOTH = "both", "AC/DC"

    class Unit(models.TextChoices):
        UNSPECIFIED = "", "—"
        PIECE = "piece", gettext_noop("Stk.")
        HOUR = "hour", gettext_noop("Std.")
        KWP = "kwp", gettext_noop("kWp")
        METER = "meter", gettext_noop("m")
        FIVE_METERS = "five_meters", gettext_noop("bis 5 m")
        TEN_METERS = "ten_meters", gettext_noop("bis 10 m")
        FLAT = "flat", gettext_noop("psch.")

    class CalculationRule(models.TextChoices):
        FIXED = "fixed", _("Фиксированная норма")
        CABLE = "cable", _("По типу кабеля и участкам 10 м")
        CONNECTION = "connection", _("По количеству подключений")
        ACTUAL = "actual", _("По фактическим человеко-часам")
        ZERO = "zero", _("Только учёт времени, цена 0")

    class PriceMode(models.TextChoices):
        PER_UNIT = "per_unit", _("За единицу")  # noqa: RUF001
        PER_NORM_HOUR = "per_norm_hour", _("За нормативный человеко-час")  # noqa: RUF001
        ACTUAL_HOURLY = "actual_hourly", _("За фактический человеко-час")  # noqa: RUF001
        ZERO = "zero", _("Без оплаты")

    code = models.SlugField(_("Код"), max_length=80, unique=True)
    name_de = models.CharField(_("Название на немецком"), max_length=255)
    name_ru = models.CharField(_("Название на русском"), max_length=255, blank=True)
    direction = models.CharField(_("Направление"), max_length=4, choices=Direction, default=Direction.AC)
    unit = models.CharField(_("Единица измерения"), max_length=16, choices=Unit, blank=True, default=Unit.UNSPECIFIED)
    calculation_rule = models.CharField(
        _("Правило расчёта"), max_length=20, choices=CalculationRule, default=CalculationRule.FIXED
    )
    price_mode = models.CharField(_("Способ цены"), max_length=20, choices=PriceMode, default=PriceMode.PER_UNIT)
    normative_hours = models.DecimalField(_("Норма, чел.-ч"), max_digits=7, decimal_places=2, default=0)
    unit_price = models.DecimalField(_("Предварительная цена, €"), max_digits=10, decimal_places=2, default=0)
    underconstruction_hours = models.DecimalField(
        _("Доплата времени за конструкцию, чел.-ч"), max_digits=7, decimal_places=2, default=0
    )
    is_break = models.BooleanField(_("Перерыв, не рабочее время"), default=False)
    is_active = models.BooleanField(_("Активен"), default=True)
    sort_order = models.PositiveIntegerField(_("Порядок"), default=0)

    objects = WorkTypeQuerySet.as_manager()

    class Meta:
        ordering: ClassVar = ["sort_order", "name_de"]

    def __str__(self):
        return (self.name_ru or self.name_de) if (get_language() or "").startswith("ru") else self.name_de

    def supports_direction(self, direction):
        if direction not in (self.Direction.AC, self.Direction.DC):
            raise ValueError("Direction must be 'ac' or 'dc'.")
        return self.direction in (direction, self.Direction.BOTH)

    @property
    def requires_route(self):
        """Требуется ли для позиции указать участок прокладки."""
        return self.calculation_rule == self.CalculationRule.CABLE or self.code == "cable-tray"

    @property
    def requires_cable_type(self):
        """Требуется ли для позиции выбрать тип кабеля."""
        return self.calculation_rule == self.CalculationRule.CABLE


class CableType(models.Model):
    """Тип кабеля задаёт норму на один начатый участок до 10 метров."""

    class Category(models.TextChoices):
        DATA = "data", _("Datenleitung")
        POTENTIAL = "potential", _("Potentialausgleich")
        CONTROL = "control", _("Steuerleitung")
        POWER = "power", _("Leistungskabel")
        HEAVY = "heavy", _("Schweres Leistungskabel")

    code = models.SlugField(_("Код"), max_length=80, unique=True)
    name_de = models.CharField(_("Название на немецком"), max_length=255)
    name_ru = models.CharField(_("Название на русском"), max_length=255, blank=True)
    category = models.CharField(_("Категория"), max_length=20, choices=Category)
    normative_hours_per_ten_meters = models.DecimalField(
        _("Норма на начатые 10 м, чел.-ч"), max_digits=7, decimal_places=2
    )
    unit_price_per_ten_meters = models.DecimalField(
        _("Предварительная цена за начатые 10 м, €"), max_digits=10, decimal_places=2, default=0
    )
    is_active = models.BooleanField(_("Активен"), default=True)
    sort_order = models.PositiveIntegerField(_("Порядок"), default=0)

    class Meta:
        ordering: ClassVar = ["sort_order", "name_de"]

    def __str__(self):
        return (self.name_ru or self.name_de) if (get_language() or "").startswith("ru") else self.name_de

    @property
    def unit_display(self):
        return "bis 5 m" if self.category == self.Category.HEAVY else "bis 10 m"


class CableRoute(models.Model):
    """Стандартный или пользовательский путь прокладки кабеля/трассы."""

    code = models.SlugField(_("Код"), max_length=80, unique=True)
    name_de = models.CharField(_("Название на немецком"), max_length=255)
    name_ru = models.CharField(_("Название на русском"), max_length=255, blank=True)
    is_active = models.BooleanField(_("Активен"), default=True)
    sort_order = models.PositiveIntegerField(_("Порядок"), default=0)

    class Meta:
        ordering: ClassVar = ["sort_order", "name_de"]

    def __str__(self):
        return (self.name_ru or self.name_de) if (get_language() or "").startswith("ru") else self.name_de


class WorkDescriptionTranslation(models.Model):
    """Утверждённые названия свободных работ без изменения первичных отчётов."""

    original = models.CharField("Исходное название", max_length=1000, unique=True)
    name_de = models.CharField("Название на немецком", max_length=1000)
    name_ru = models.CharField("Название на русском", max_length=1000)

    class Meta:
        ordering: ClassVar = ["original"]

    def __str__(self):
        return (self.name_ru or self.name_de) if (get_language() or "").startswith("ru") else self.name_de
