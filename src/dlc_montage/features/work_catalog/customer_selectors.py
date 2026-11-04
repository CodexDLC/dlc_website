"""Read access to customer price positions."""

from .models import CustomerWorkPosition


def customer_positions():
    return CustomerWorkPosition.objects.filter(is_active=True).order_by("sort_order", "code")


def all_customer_positions():
    return CustomerWorkPosition.objects.order_by("sort_order", "code")
