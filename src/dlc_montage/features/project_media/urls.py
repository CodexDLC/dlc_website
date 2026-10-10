from django.urls import path

from . import views

app_name = "project_media"
urlpatterns = [
    path("group/<int:group_id>/", views.files, name="list"),
    path("<int:pk>/preview/", views.preview, name="preview"),
    path("<int:pk>/download/", views.download, name="download"),
    path("<int:pk>/publicity/", views.publicity, name="publicity"),
]
