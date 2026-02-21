# 📜 Services Views (`services.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../../README.md)

This `services.py` module defines Django views for displaying service-related content on the Lily Website. It includes a view for an index of all services (grouped by categories) and a detail view for individual service categories.

## Purpose

These views are responsible for presenting the salon's services to users, allowing them to browse available treatments and view details for each category.

## `ServicesIndexView` Class

The `ServicesIndexView` displays a comprehensive list of services, organized into "bento grid" islands, which can optionally be filtered by a `bento_group`.

### Attributes

*   `template_name = "services/services.html"`:
    Specifies the path to the HTML template that this view will render.

### `get_context_data()` Method

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)

    # Get bento_group filter from query params (optional)
    bento_filter = self.request.GET.get("bento", None)

    # Get islands (categories grouped by bento_group)
    context["islands"] = CategorySelector.get_for_price_list(bento_group=bento_filter)

    # SEO
    context["seo"] = SeoSelector.get_seo("services_index")

    # Filter info for template
    context["bento_filter"] = bento_filter

    return context
```

### Description

This method is overridden to add custom data to the template context before rendering the `services/services.html` template.

### Process

1.  `context = super().get_context_data(**kwargs)`: Calls the parent `TemplateView`'s `get_context_data` method to retrieve the default context.
2.  **Bento Group Filter:** Retrieves the `bento` query parameter from the request, allowing users to filter services by a specific group.
3.  **Service Islands Data:** Fetches service categories grouped into "islands" (for a price list display) using `CategorySelector.get_for_price_list()`, optionally applying the `bento_filter`. This data is added to the context under the key `"islands"`.
4.  **SEO Data:** Retrieves SEO-related data for the "services index" page using `SeoSelector.get_seo("services_index")` and adds it to the context under the key `"seo"`.
5.  **Filter Info:** Adds the `bento_filter` value to the context for use in the template.
6.  `return context`: Returns the augmented context dictionary.

## `ServiceDetailView` Class

The `ServiceDetailView` displays detailed information for a single service category.

### Attributes

*   `model = Category`:
    Specifies that this view operates on the `Category` model.
*   `template_name = "services/detail.html"`:
    Specifies the path to the HTML template for displaying category details.
*   `context_object_name = "category"`:
    The name of the variable that will contain the `Category` object in the template context.
*   `slug_url_kwarg = "slug"`:
    The name of the URL keyword argument that contains the category's slug.

### `get_object()` Method

```python
def get_object(self, queryset=None):
    slug = self.kwargs.get(self.slug_url_kwarg)
    category = CategorySelector.get_detail(slug)
    if not category:
        raise Http404("Category not found")
    return category
```

### Description

This method is overridden to retrieve a single `Category` object based on its slug from the URL.

### Process

1.  **Retrieve Slug:** Extracts the `slug` from the URL keyword arguments.
2.  **Fetch Category:** Uses `CategorySelector.get_detail(slug)` to fetch the `Category` object.
3.  **Handle Not Found:** If no category is found for the given slug, it raises an `Http404` exception.
4.  `return category`: Returns the fetched `Category` object.

### `get_context_data()` Method

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    return context
```

### Description

This method retrieves the context data for the `ServiceDetailView`. Currently, it only calls the parent method, implying that most of the necessary data is already available through `context_object_name`.

## Dependencies

*   `CategorySelector` (from `..selectors.categories`): Used to retrieve category data.
*   `SeoSelector` (from `...system.selectors.seo`): Used to retrieve SEO metadata.
*   `Category` (from `..models`): The model used by `ServiceDetailView`.
