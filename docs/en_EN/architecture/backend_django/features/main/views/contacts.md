# 📜 Contact View (`contacts.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../../README.md)

This `contacts.py` module defines the `ContactsView` class, which handles the contact page and form submissions for the Lily Website. It extends Django's generic `FormView` and integrates with HTMX for dynamic form handling.

## `ContactsView` Class

The `ContactsView` manages the display of the contact form, processes submissions, and interacts with a `ContactService` to handle contact requests.

### Attributes

*   `template_name = "contacts/contacts.html"`:
    Specifies the path to the HTML template that this view will render.
*   `form_class = ContactForm`:
    Defines the Django form class (`ContactForm`) to be used for the contact form.
*   `success_url = "/contacts/"`:
    The URL to redirect to upon successful form submission (for non-HTMX requests).

### `get_context_data()` Method

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)

    # Ensure form is in context
    if "form" not in context:
        context["form"] = self.get_form()

    context["settings"] = SiteSettings.load()
    context["seo"] = SeoSelector.get_seo("contacts")
    return context
```

### Description

This method is overridden to add custom data to the template context before rendering the `contacts/contacts.html` template.

### Process

1.  `context = super().get_context_data(**kwargs)`: Calls the parent `FormView`'s `get_context_data` method to retrieve the default context.
2.  **Form in Context:** Ensures that the form instance is present in the context, creating it if necessary.
3.  **Site Settings:** Loads global site settings using `SiteSettings.load()` and adds them to the context under the key `"settings"`.
4.  **SEO Data:** Retrieves SEO-related data for the "contacts" page using `SeoSelector.get_seo("contacts")` and adds it to the context under the key `"seo"`.
5.  `return context`: Returns the augmented context dictionary.

### `form_valid()` Method

```python
def form_valid(self, form):
    # Create request via Service
    ContactService.create_request(
        first_name=form.cleaned_data["first_name"],
        last_name=form.cleaned_data["last_name"],
        contact_type=form.cleaned_data["contact_type"],
        contact_value=form.cleaned_data["contact_value"],
        message=form.cleaned_data["message"],
        topic=form.cleaned_data["topic"],
        consent_marketing=form.cleaned_data["consent_marketing"],
    )

    # HTMX Response
    if self.request.headers.get("HX-Request"):
        return render(self.request, "contacts/partials/success_message.html")

    return super().form_valid(form)
```

### Description

This method is called when the submitted form data is valid. It processes the form data and handles the response, especially for HTMX requests.

### Process

1.  **Create Contact Request:** Calls `ContactService.create_request()` to process the cleaned form data, delegating the business logic for handling contact requests to a service.
2.  **HTMX Response:**
    *   If the request is an HTMX request (`HX-Request` header is present), it renders a partial HTML template (`contacts/partials/success_message.html`) to display a success message dynamically.
    *   Otherwise, it calls `super().form_valid(form)` to perform the default `FormView` behavior (typically a redirect to `success_url`).

### `form_invalid()` Method

```python
def form_invalid(self, form):
    if self.request.headers.get("HX-Request"):
        return render(self.request, "contacts/partials/form.html", {"form": form})
    return super().form_invalid(form)
```

### Description

This method is called when the submitted form data is invalid. It handles the response, especially for HTMX requests.

### Process

1.  **HTMX Response:**
    *   If the request is an HTMX request, it renders a partial HTML template (`contacts/partials/form.html`) with the invalid form, allowing HTMX to update only the form section with validation errors.
    *   Otherwise, it calls `super().form_invalid(form)` to perform the default `FormView` behavior (re-render the form with errors).

## Dependencies

*   `ContactForm` (from `..forms`): The form class used for contact submissions.
*   `ContactService` (from `..services.contact_service`): The service responsible for processing contact requests.
*   `SiteSettings` (from `features.system.models.site_settings`): Used to load global site settings.
*   `SeoSelector` (from `features.system.selectors.seo`): Used to retrieve SEO metadata.

## Templates

*   `contacts/contacts.html`: The main template for the contact page.
*   `contacts/partials/success_message.html`: Partial template for displaying a success message via HTMX.
*   `contacts/partials/form.html`: Partial template for re-rendering the form with errors via HTMX.
