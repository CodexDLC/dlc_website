# 📜 Team View (`team.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../../README.md)

This `team.py` module defines the `TeamView` class, which is responsible for rendering the team page of the Lily Website. It extends Django's generic `TemplateView` and populates the template context with data about the salon's team members, site settings, and SEO information.

## `TeamView` Class

The `TeamView` handles requests to the team page, fetching and preparing data for display.

### Attributes

*   `template_name = "team/team.html"`:
    Specifies the path to the HTML template that this view will render.

### `get_context_data()` Method

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)

    # Masters
    context["owner"] = MasterSelector.get_owner()
    context["team"] = MasterSelector.get_team_members()

    # Settings (for hiring block)
    context["settings"] = SiteSettings.load()

    # SEO
    context["seo"] = SeoSelector.get_seo("team")

    return context
```

### Description

This method is overridden to add custom data to the template context before rendering the `team/team.html` template.

### Process

1.  `context = super().get_context_data(**kwargs)`: Calls the parent `TemplateView`'s `get_context_data` method to retrieve the default context.
2.  **Masters Data:**
    *   `context["owner"] = MasterSelector.get_owner()`: Fetches information about the salon owner using `MasterSelector.get_owner()` and adds it to the context under the key `"owner"`.
    *   `context["team"] = MasterSelector.get_team_members()`: Fetches a list of all team members using `MasterSelector.get_team_members()` and adds it to the context under the key `"team"`.
3.  **Site Settings:**
    *   `context["settings"] = SiteSettings.load()`: Loads global site settings using `SiteSettings.load()` and adds them to the context under the key `"settings"`. This might be used for displaying information like a "hiring" block.
4.  **SEO Data:**
    *   `context["seo"] = SeoSelector.get_seo("team")`: Retrieves SEO-related data for the "team" page using `SeoSelector.get_seo("team")` and adds it to the context under the key `"seo"`.
5.  `return context`: Returns the augmented context dictionary.

## Dependencies

*   `MasterSelector` (from `features.booking.selectors.masters`): Used to retrieve data about salon masters and team members.
*   `SiteSettings` (from `features.system.models.site_settings`): Used to load global site settings.
*   `SeoSelector` (from `features.system.selectors.seo`): Used to retrieve SEO metadata.

## Template

The `TeamView` renders the `team/team.html` template, which is expected to utilize the `owner`, `team`, `settings`, and `seo` data provided in the context.
