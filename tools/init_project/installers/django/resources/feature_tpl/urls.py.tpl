from django.urls import path

from .views import home

app_name = "{{APP_NAME}}"

urlpatterns = [
    path("", home.index, name="index"),
]
