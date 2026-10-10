from django.urls import path

from .views import ContactFormView

app_name = "conversations"

urlpatterns = [
    path("contact/", ContactFormView.as_view(), name="contact"),
]
