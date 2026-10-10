from django.urls import path

from .views import teams

app_name = "crews"
urlpatterns = [path("", teams, name="list"), path("<int:pk>/", teams, name="edit")]
