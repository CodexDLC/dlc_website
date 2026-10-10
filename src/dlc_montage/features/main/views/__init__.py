from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "main/home.html"


class ContactsView(TemplateView):
    template_name = "main/contacts.html"
