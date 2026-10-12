from django.urls import path

from . import views

app_name = "demo"

urlpatterns = [
    path("", views.home, name="home"),
    path("taetigkeiten/", views.work_types, name="work_types"),
    path("taetigkeiten/neu/", views.work_type_edit, name="work_type_new"),
    path("taetigkeiten/<int:pk>/", views.work_type_edit, name="work_type_edit"),
    path("berichte/", views.reports, name="reports"),
    path("berichte/neu/", views.report_edit, name="report_new"),
    path("berichte/<int:pk>/bearbeiten/", views.report_edit, name="report_edit"),
    path("berichte/<int:pk>/", views.report_detail, name="report_detail"),
    path("berichte/<int:pk>/excel/", views.report_download, name="report_download"),
    path("zuruecksetzen/", views.reset, name="reset"),
]
