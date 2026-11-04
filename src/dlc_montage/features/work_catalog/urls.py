from django.urls import path

from .customer_catalog import customer_catalog
from .views import catalog

app_name = "work_catalog"
urlpatterns = [
    path("", catalog, name="list"),
    path("customer/", customer_catalog, name="customer_list"),
    path("customer/<int:pk>/", customer_catalog, name="customer_edit"),
    path("<int:pk>/", catalog, name="edit"),
]
