"""Клиентские права, предложения плана, приёмка и неизменяемый аудит."""

from typing import ClassVar

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ClientMembership(models.Model):
    """Явное назначение одного заказчика пользователю; почта не даёт доступа."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="client_membership")
    client = models.ForeignKey("projects.Client", on_delete=models.PROTECT, related_name="memberships")
    is_active = models.BooleanField(default=True)
    can_manage_projects = models.BooleanField(default=False)
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="granted_clients")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar = ["user_id"]


class PlanProposal(models.Model):
    """Отдельный проект плана до явного решения администратора."""

    site = models.ForeignKey("projects.AcObject", on_delete=models.PROTECT, related_name="customer_plan_proposals")
    proposed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    payload = models.JSONField()
    status = models.CharField(
        max_length=12,
        default="pending",
        choices=[
            ("pending", _("Ожидает")),
            ("approved", _("Утверждено")),
            ("rejected", _("Отклонено")),
        ],
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="decided_plan_proposals"
    )
    decision_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering: ClassVar = ["-created_at", "-pk"]


class SiteReview(models.Model):
    """Заказческая проверка, независимая от готовности Standort и оплаты."""

    site = models.OneToOneField("projects.AcObject", on_delete=models.PROTECT, related_name="customer_review")
    status = models.CharField(
        max_length=12,
        default="draft",
        choices=[
            ("draft", _("Не отправлено")),
            ("submitted", _("На проверке")),
            ("accepted", _("Без замечаний")),
            ("returned", _("С замечаниями")),
        ],
    )
    snapshot_digest = models.CharField(max_length=64, blank=True)
    work_snapshot = models.JSONField(default=list, blank=True)
    item_decisions = models.JSONField(default=dict, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="submitted_site_reviews"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="decided_site_reviews"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    remark = models.TextField(blank=True)


class CustomerAuditEvent(models.Model):
    """Аудит клиентского контура без копии финансовых или секретных данных."""

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    client = models.ForeignKey("projects.Client", on_delete=models.PROTECT, related_name="customer_audit_events")
    action = models.CharField(max_length=48)
    target_type = models.CharField(max_length=32)
    target_id = models.PositiveBigIntegerField()
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar = ["-created_at", "-pk"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Исторический аудит не редактируется.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Исторический аудит не удаляется.")
