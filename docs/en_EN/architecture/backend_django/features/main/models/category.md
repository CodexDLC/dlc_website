# 📜 Category Model (`category.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../../README.md)

This `category.py` module defines the `Category` model, which represents service categories (e.g., Manicure, Pedicure, Haircut) within the `main` feature. It inherits from `TimestampMixin`, `ActiveMixin`, and `SeoMixin` for common fields and behaviors, and includes functionality for grouping categories into a "bento grid" on the main page.

## `Category` Model

The `Category` model (`Category(TimestampMixin, ActiveMixin, SeoMixin)`) organizes services into logical groups.

### `BENTO_GROUPS`

```python
BENTO_GROUPS = [
    ("hair", _("Friseur & Styling")),
    ("nails", _("Nagelservice")),
    ("face", _("Kosmetologie")),
    ("eyes", _("Brows & Lashes")),
    ("body", _("Massage & Relax")),
    ("hair_removal", _("Depilation")),
]
```
A list of tuples defining predefined groups for organizing categories on the main page's "bento grid" layout. Each tuple contains a machine-readable key and a human-readable (translatable) display name.

### Fields

*   `title` (`CharField`):
    The name of the category (e.g., 'Maniküre').
*   `slug` (`SlugField`):
    A URL-friendly identifier for the category, must be unique.
*   `bento_group` (`CharField`):
    Assigns the category to one of the `BENTO_GROUPS`. This is used for display on the main page.
*   `image` (`ImageField`):
    A background image for the category's Hero section and Bento card. Images are optimized on save.
*   `description` (`TextField`, optional):
    A short description displayed in the Hero section.
*   `content` (`TextField`, optional):
    Detailed SEO text or content displayed at the bottom of the category page.
*   `icon` (`FileField`, optional):
    An SVG icon for use in menus or footers.
*   `order` (`PositiveIntegerField`):
    Determines the sorting order of categories (lower numbers come first).

### Meta Class

*   `verbose_name`, `verbose_name_plural`: Human-readable names for the model.
*   `ordering = ["order", "title"]`: Default ordering for category instances.

### `__str__()` Method

Returns a string representation of the category, including its title and bento group display name.

### `save()` Method

```python
def save(self, *args, **kwargs):
    if self.image:
        optimize_image(self.image, max_width=1200)
    super().save(*args, **kwargs)
    # Targeted cache invalidation
    cache.delete_many(["active_categories_cache", "bento_grid_cache", f"category_detail_{self.slug}"])
```
Overrides the default `save()` method to:
1.  **Optimize Image:** If an `image` is provided, it calls `optimize_image()` to resize it.
2.  **Call Super Save:** Calls the parent `save()` method to persist the instance.
3.  **Cache Invalidation:** Invalidates relevant cache keys (`active_categories_cache`, `bento_grid_cache`, `category_detail_{slug}`) to ensure that updated data is fetched fresh.

### `get_absolute_url()` Method

```python
def get_absolute_url(self):
    from django.urls import reverse
    return reverse("category_detail", kwargs={"slug": self.slug})
```
Returns the absolute URL for a category instance, using its slug.
