"""
dlc_website — URL Configuration.

Features auto-included via include().
API via Django Ninja at /api/.
"""

from django.contrib import admin
from django.urls import include, path

from api.urls import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("", include("features.main.urls")),
]
