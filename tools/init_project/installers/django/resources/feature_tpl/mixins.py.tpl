"""
Base model mixins for the project.

Usage:
    from features.system.models.mixins import TimestampMixin

    class MyModel(TimestampMixin, models.Model):
        ...
"""

from django.db import models


class TimestampMixin(models.Model):
    """Adds created_at and updated_at fields."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
