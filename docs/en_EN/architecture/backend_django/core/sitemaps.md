# 📜 Sitemaps Configuration (`sitemaps.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

This `sitemaps.py` module defines the sitemap configurations for the Django backend application. It includes a sitemap for static pages and integrates sitemaps from other features (e.g., categories), allowing search engines to efficiently crawl and index the website's content.

## Purpose

The module centralizes the definition of sitemaps, which are XML files that list the URLs of a site. Sitemaps help search engines discover all the pages on a website, especially those that might not be found through regular crawling.

## `StaticSitemap` Class

```python
class StaticSitemap(Sitemap):
    priority = 0.8
    changefreq = "monthly"

    def items(self):
        return ["home", "services", "team", "contacts", "impressum", "datenschutz"]

    def location(self, item):
        return reverse(item)
```

### Description

This `Sitemap` subclass generates entries for static pages of the website.

### Attributes

*   `priority = 0.8`:
    Indicates the priority of these URLs relative to other URLs on the site (0.0 to 1.0).
*   `changefreq = "monthly"`:
    Suggests to search engines how frequently the content at these URLs is likely to change.

### Methods

*   `items()`:
    Returns a list of view names (as strings) for which sitemap entries should be generated. These view names are then resolved to actual URLs using `reverse()`.
*   `location(self, item)`:
    Returns the absolute URL for each item in the `items()` list by reversing the view name.

## `sitemaps` Dictionary

```python
sitemaps = {
    "static": StaticSitemap,
    "categories": CategorySitemap,
}
```

### Description

This dictionary aggregates all sitemap classes into a single object that can be passed to Django's sitemap view.

### Contents

*   `"static"`: Maps the key `static` to the `StaticSitemap` class.
*   `"categories"`: Maps the key `categories` to the `CategorySitemap` class, which is imported from `features.main.sitemaps`. This indicates that the `main` feature provides its own sitemap for categories.

## Usage

The `sitemaps` dictionary is imported into the root `urls.py` (`core/urls.py`) and passed to Django's `sitemap` view:

```python
path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
```
This configuration makes the sitemap accessible at `/sitemap.xml`.

## Example for Model-Based Sitemaps (Commented Out)

The module also includes commented-out example code for how to create sitemaps for Django models (e.g., `ServiceSitemap`), demonstrating how to define `changefreq`, `priority`, `items()`, and `lastmod()` methods for dynamic content.
