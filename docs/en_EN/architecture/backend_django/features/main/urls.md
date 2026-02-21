# 📜 URL Configuration (`urls.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This `urls.py` file defines the URL patterns for the `main` Django application (feature). It maps specific URL paths to the views responsible for rendering the main public-facing pages of the Lily Website.

## Purpose

This module centralizes the URL routing for the `main` feature, making it easy to manage and understand how different web pages are accessed.

## URL Patterns

```python
urlpatterns = [
    # Home
    path("", home.HomeView.as_view(), name="home"),
    # Services Index (Price List)
    path("services/", services.ServicesIndexView.as_view(), name="services"),
    # Service Detail (Dynamic by slug)
    path("services/<slug:slug>/", services.ServiceDetailView.as_view(), name="service_detail"),
    # Team
    path("team/", team.TeamView.as_view(), name="team"),
    # Contacts
    path("contacts/", contacts.ContactsView.as_view(), name="contacts"),
    # Legal
    path("impressum/", legal.ImpressumView.as_view(), name="impressum"),
    path("datenschutz/", legal.DatenschutzView.as_view(), name="datenschutz"),
    path("faq/", legal.FaqView.as_view(), name="faq"),
]
```

### Breakdown

*   **Home Page:**
    *   `path("", home.HomeView.as_view(), name="home")`: Maps the root URL (`/`) to the `HomeView`, serving as the website's homepage. The `name="home"` allows for easy referencing of this URL throughout the project.
*   **Services Index:**
    *   `path("services/", services.ServicesIndexView.as_view(), name="services")`: Maps `/services/` to the `ServicesIndexView`, which displays a list of all services.
*   **Service Detail:**
    *   `path("services/<slug:slug>/", services.ServiceDetailView.as_view(), name="service_detail")`: Maps dynamic URLs like `/services/classic-manicure/` to the `ServiceDetailView`. The `<slug:slug>` part captures a URL-friendly string (slug) from the URL and passes it as an argument to the view, allowing it to fetch specific service category details.
*   **Team Page:**
    *   `path("team/", team.TeamView.as_view(), name="team")`: Maps `/team/` to the `TeamView`, displaying information about the salon's team.
*   **Contacts Page:**
    *   `path("contacts/", contacts.ContactsView.as_view(), name="contacts")`: Maps `/contacts/` to the `ContactsView`, which handles the contact form.
*   **Legal Pages:**
    *   `path("impressum/", legal.ImpressumView.as_view(), name="impressum")`: Maps `/impressum/` to the `ImpressumView` for the imprint page.
    *   `path("datenschutz/", legal.DatenschutzView.as_view(), name="datenschutz")`: Maps `/datenschutz/` to the `DatenschutzView` for the privacy policy page.
    *   `path("faq/", legal.FaqView.as_view(), name="faq")`: Maps `/faq/` to the `FaqView` for the FAQ page.

## Dependencies

This module imports views from the local `views` module (`.views`), which contains `home`, `contacts`, `legal`, `services`, and `team` views.
