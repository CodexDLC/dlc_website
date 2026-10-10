from django.shortcuts import redirect
from django.views.generic import FormView

from ..forms import ContactForm
from ..models import Message


class ContactFormView(FormView):
    template_name = "features/main/contacts.html"
    form_class = ContactForm

    def get_success_url(self):
        return self.request.path + "?sent=1"

    def form_valid(self, form):
        message = form.save(commit=False)
        message.source = Message.Source.CONTACT_FORM
        message.channel = Message.Channel.EMAIL
        message.save()
        from ..services import notify_new_message

        notify_new_message(message)
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sent"] = self.request.GET.get("sent") == "1"
        return context
