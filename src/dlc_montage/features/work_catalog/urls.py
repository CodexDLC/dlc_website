from django.urls import path

from .views import catalog

app_name = "work_catalog"
urlpatterns = [path("", catalog, name="list"), path("<int:pk>/", catalog, name="edit")]
