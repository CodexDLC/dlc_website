from codex_django.core.sitemaps import BaseSitemap
from django.conf import settings

# Import other specific sitemaps from features here as needed
# from features.main.sitemaps import CategorySitemap


class StaticSitemap(BaseSitemap):
    """
    Sitemap for static pages that don't depend on models.
    """
    priority = 0.5
    changefreq = "monthly"

    def items(self):
        # Configuration for static pages is usually in core/settings/modules/sitemap.py
        # but you can also provide a hardcoded list here.
        return getattr(settings, "SITEMAP_STATIC_PAGES", ["home"])


# Example of how to structure the sitemaps dict for URLs
# You can add feature sitemaps here as well.
sitemaps = {
    "static": StaticSitemap,
    # "categories": CategorySitemap,
}
