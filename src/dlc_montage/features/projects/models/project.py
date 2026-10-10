"""Заказчики и отдельные AC-объекты общего проекта."""

from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class Client(models.Model):
    """Компания-заказчик."""

    name = models.CharField(_("Название"), max_length=255, unique=True)
    contact_name = models.CharField(_("Контактное лицо"), max_length=255, blank=True)
    contact_email = models.EmailField(_("Электронная почта"), blank=True)
    contact_phone = models.CharField(_("Телефон"), max_length=50, blank=True)
    is_active = models.BooleanField(_("Активен"), default=True)

    class Meta:
        ordering: ClassVar = ["name"]

    def __str__(self):
        return self.name


class AcObject(models.Model):
    """Дом/подъезд с номером заказчика; номер обязателен при экспорте."""

    group = models.ForeignKey("projects.ProjectGroup", on_delete=models.PROTECT, related_name="ac_objects")
    name = models.CharField(_("Дом / подъезд"), max_length=200)
    address = models.CharField(_("Адрес"), max_length=500, blank=True)
    project_number = models.CharField(_("Номер проекта заказчика (P/Nr)"), max_length=100, blank=True)
    status = models.CharField(
        _("Готовность Standort"),
        max_length=16,
        default="not_started",
        choices=[
            ("not_started", _("Не начато")),
            ("started", _("Начато")),
            ("completed", _("Завершено")),
        ],
    )
    is_paid = models.BooleanField(_("Zahlungsstatus Bezahlt"), default=False)
    paid_at = models.DateTimeField(_("Bezahlt am"), null=True, blank=True)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="paid_ac_objects",
        verbose_name=_("Bezahlt von"),
    )
    payment_note = models.CharField(_("Zahlungsnotiz"), max_length=255, blank=True, default="")
    is_active = models.BooleanField(_("Активен"), default=True)

    class Meta:
        ordering: ClassVar = ["name", "pk"]
        constraints: ClassVar = [models.UniqueConstraint(fields=["group", "name"], name="unique_ac_object_name")]

    def __str__(self):
        return self.name

    @property
    def status_display(self) -> str:
        return str(self.get_status_display())

    def delete(self, *args, **kwargs):
        raise ValidationError(_("Объект сохраняется в истории. Отметьте его неактивным."))
