from django.urls import path

from .views import ContactsView, HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("contacts/", ContactsView.as_view(), name="contacts"),
]
