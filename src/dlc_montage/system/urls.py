from typing import Any

from django.urls import path

from .views.health import health_check

app_name = "system"

urlpatterns: list[Any] = [
    path("health/", health_check, name="health_check"),
]
