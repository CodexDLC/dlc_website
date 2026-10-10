"""Маршруты отчётов; feature можно подключить к другой оболочке."""

from django.urls import path

from . import views

app_name = "internal_time"
urlpatterns = [
    path("", views.report_list, name="list"),
    path("new/", views.report_editor, name="new"),
    path("<int:pk>/", views.report_detail, name="detail"),
    path("<int:pk>/edit/", views.report_editor, name="edit"),
    path("<int:pk>/review/", views.report_review, name="review"),
]
