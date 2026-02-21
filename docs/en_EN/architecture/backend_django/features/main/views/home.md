# 📜 Home View (`home.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../../README.md)

This `home.py` module defines the `HomeView` class, which is responsible for rendering the main homepage of the Lily Website. It extends Django's generic `TemplateView` and populates the template context with data required for the bento grid layout and SEO.

## `HomeView` Class

The `HomeView` handles requests to the homepage, fetching and preparing data for display.

### Attributes

*   `template_name = "home/home.html"`:
    Specifies the path to the HTML template that this view will render.

### `get_context_data()` Method

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)

    # 1. Bento Grid Data (Categories grouped by bento_group)
    context["bento"] = HomeService.get_bento_context()

    # 2. SEO Data
    context["seo"] = SeoSelector.get_seo("home")

    return context
```

### Description

This method is overridden to add custom data to the template context before rendering the `home/home.html` template.

### Process

1.  `context = super().get_context_data(**kwargs)`: Calls the parent `TemplateView`'s `get_context_data` method to retrieve the default context.
2.  **Bento Grid Data:**
    *   `context["bento"] = HomeService.get_bento_context()`: Fetches data related to the "bento grid" layout (categories grouped by `bento_group`) using `HomeService.get_bento_context()` and adds it to the context under the key `"bento"`.
3.  **SEO Data:**
    *   `context["seo"] = SeoSelector.get_seo("home")`: Retrieves SEO-related data for the "home" page using `SeoSelector.get_seo("home")` and adds it to the context under the key `"seo"`.
4.  `return context`: Returns the augmented context dictionary.

## Dependencies

*   `HomeService` (from `..services.home_service`): Used to retrieve data for the bento grid.
*   `SeoSelector` (from `...system.selectors.seo`): Used to retrieve SEO metadata.

## Template

The `HomeView` renders the `home/home.html` template, which is expected to utilize the `bento` and `seo` data provided in the context.
