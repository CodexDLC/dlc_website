# 📜 Service Model (`service.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../../README.md)

This `service.py` module defines the Django models for `Service` and `PortfolioImage` within the `main` feature. These models represent the core data structures for individual services offered by the salon and their associated gallery images.

## `Service` Model

The `Service` model (`Service(TimestampMixin, ActiveMixin, SeoMixin)`) represents a specific service (e.g., 'Classic Manicure'). It inherits from `TimestampMixin`, `ActiveMixin`, and `SeoMixin` for common fields and behaviors.

### Fields

*   `category` (`ForeignKey` to `Category`):
    Links the service to a `Category`.
    *   `on_delete=models.CASCADE`: If the category is deleted, all associated services are also deleted.
    *   `related_name="services"`: Allows accessing services from a category instance (e.g., `category.services.all()`).
*   `title` (`CharField`):
    The name of the service (e.g., 'Klassische Maniküre').
*   `slug` (`SlugField`):
    A URL-friendly identifier for the service, must be unique.
*   `price` (`DecimalField`):
    The base price of the service.
*   `price_info` (`CharField`, optional):
    Custom text to display for the price (e.g., 'ab 30€'). If empty, the `price` field is used.
*   `duration` (`PositiveIntegerField`):
    The duration of the service in minutes.
*   `duration_info` (`CharField`, optional):
    Custom text to display for the duration (e.g., 'ca. 45-60 Min'). If empty, the `duration` field is used.
*   `description` (`TextField`, optional):
    A short description displayed in list views.
*   `content` (`TextField`, optional):
    Detailed description or article about the service (supports HTML/Markdown).
*   `image` (`ImageField`, optional):
    A photo of the specific service. Images are optimized on save.
*   `is_hit` (`BooleanField`):
    A flag to highlight the service as popular or a "hit".
*   `order` (`PositiveIntegerField`):
    Determines the sorting order of services.

### Meta Class

*   `verbose_name`, `verbose_name_plural`: Human-readable names for the model.
*   `ordering = ["order", "title"]`: Default ordering for service instances.

### `__str__()` Method

Returns the `title` of the service for string representation.

### `save()` Method

```python
def save(self, *args, **kwargs):
    if self.image:
        optimize_image(self.image, max_width=1200)
    super().save(*args, **kwargs)
    # Targeted cache invalidation
    try:
        cache.delete_many(
            [
                "active_services_cache",
                "popular_services_cache",
                f"service_detail_{self.slug}",
                f"category_detail_{self.category.slug}",
            ]
        )
    except Exception:
        # Fail silently if cache/redis is down
        pass
```
Overrides the default `save()` method to:
1.  **Optimize Image:** If an `image` is provided, it calls `optimize_image()` to resize it.
2.  **Call Super Save:** Calls the parent `save()` method to persist the instance.
3.  **Cache Invalidation:** Invalidates relevant cache keys (`active_services_cache`, `popular_services_cache`, `service_detail_{slug}`, `category_detail_{category_slug}`) to ensure that updated data is fetched fresh. Errors during cache invalidation are silently suppressed.

## `PortfolioImage` Model

The `PortfolioImage` model (`PortfolioImage(TimestampMixin)`) represents gallery images associated with a specific service. These images can be used for "Before/After" examples or general portfolio display.

### Fields

*   `service` (`ForeignKey` to `Service`):
    Links the image to a `Service`.
    *   `on_delete=models.CASCADE`: If the service is deleted, associated portfolio images are also deleted.
    *   `related_name="portfolio_images"`: Allows accessing images from a service instance (e.g., `service.portfolio_images.all()`).
*   `image` (`ImageField`):
    The image file. Images are optimized on save.
*   `title` (`CharField`, optional):
    An optional caption or description for the image.
*   `order` (`PositiveIntegerField`):
    Determines the sorting order of images within a service's gallery.

### Meta Class

*   `verbose_name`, `verbose_name_plural`: Human-readable names for the model.
*   `ordering = ["order", "created_at"]`: Default ordering for portfolio images.

### `__str__()` Method

Returns a string representation indicating the service the image belongs to.

### `save()` Method

```python
def save(self, *args, **kwargs):
    if self.image:
        optimize_image(self.image, max_width=1600)
    super().save(*args, **kwargs)
    # Targeted cache invalidation
    try:
        cache.delete_many([f"service_detail_{self.service.slug}", f"category_detail_{self.service.category.slug}"])
    except Exception:
        pass
```
Overrides the default `save()` method to:
1.  **Optimize Image:** If an `image` is provided, it calls `optimize_image()` to resize it.
2.  **Call Super Save:** Calls the parent `save()` method to persist the instance.
3.  **Cache Invalidation:** Invalidates relevant cache keys (`service_detail_{service_slug}`, `category_detail_{category_slug}`) to ensure that updated data is fetched fresh. Errors during cache invalidation are silently suppressed.
