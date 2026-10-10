"""Общие проекты (Anlagen) для внутреннего учёта AC и DC."""

from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class ProjectGroup(models.Model):
    """Общий объект; номер отдельного AC-подъезда здесь не требуется."""

    name = models.CharField(_("Название"), max_length=255)
    client = models.ForeignKey(
        "projects.Client", null=True, blank=True, on_delete=models.PROTECT, verbose_name=_("Заказчик")
    )
    capacity_kw = models.DecimalField(
        _("Мощность, кВт"), max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    address = models.CharField(_("Адрес"), max_length=500, blank=True)
    additional_addresses = models.TextField(_("Дополнительные адреса"), blank=True)
    maps_url = models.URLField(_("Ссылка Google Maps"), blank=True)
    starts_on = models.DateField(_("Начало работ"), null=True, blank=True)
    ends_on = models.DateField(_("Завершение работ"), null=True, blank=True)
    ac_status = models.CharField(
        _("Готовность AC"),
        max_length=16,
        default="not_started",
        choices=[("not_started", _("Не начато")), ("started", _("Начато")), ("completed", _("Завершено"))],
    )
    dc_status = models.CharField(
        _("Готовность DC"),
        max_length=16,
        default="not_started",
        choices=[("not_started", _("Не начато")), ("started", _("Начато")), ("completed", _("Завершено"))],
    )
    has_ac = models.BooleanField(_("Работы AC"), default=True)
    has_dc = models.BooleanField(_("Работы DC"), default=True)
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=_("Ответственный"),
    )
    deputy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="deputy_projects",
        verbose_name=_("Заместитель"),
    )
    ac_responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ac_projects",
        verbose_name=_("Ответственный AC"),
    )
    dc_responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="dc_projects",
        verbose_name=_("Ответственный DC"),
    )
    status = models.CharField(
        _("Статус"),
        max_length=16,
        default="active",
        choices=[
            ("active", _("Активен")),
            ("completed", _("Завершён")),
            ("cancelled", _("Отменён")),
            ("archived", _("Архив")),
            ("deleted", _("Удалён")),
        ],
    )
    edit_level = models.CharField(
        _("Кто может редактировать"),
        max_length=16,
        default="admin",
        choices=[("admin", _("Администратор")), ("foreman", _("Назначенный бригадир"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar = ["name", "pk"]
        verbose_name = _("группа проектов")
        verbose_name_plural = "Группы проектов"
        permissions: ClassVar = [("quick_create_projectgroup", _("Создавать минимальные группы проектов"))]

    def __str__(self):
        return self.name

    def clean(self):
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValidationError(_("Завершение не может быть раньше начала."))
        if not self.has_ac and not self.has_dc:
            raise ValidationError(_("Выберите хотя бы одно направление."))

    def delete(self, *args, **kwargs):
        raise ValidationError(_("Проекты не удаляются физически. Используйте статус «Удалён»."))
