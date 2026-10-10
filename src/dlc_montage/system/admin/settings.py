from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from ..models.settings import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """
    Admin for site settings.
    Only one record is expected (Singleton pattern).
    """

    list_display = ("__str__", "app_mode_enabled", "maintenance_mode")

    fieldsets = (
        (_("Основные контакты"), {
            "fields": (
                "phone", "email", "address_street", "address_locality",
                "address_postal_code", "contact_person", "working_hours",
            )
        }),
        (_("Гео-данные"), {
            "fields": ("google_maps_link", "latitude", "longitude"),
            "classes": ("collapse",)
        }),
        (_("Социальные сети"), {
            "fields": (
                "instagram_url", "facebook_url", "telegram_url", "whatsapp_url",
                "youtube_url", "linkedin_url", "tiktok_url", "twitter_url",
                "pinterest_url",
            ),
            "classes": ("collapse",)
        }),
        (_("Маркетинг и аналитика"), {
            "fields": (
                "google_analytics_id", "google_tag_manager_id",
                "facebook_pixel_id", "tiktok_pixel_id",
            ),
            "classes": ("collapse",)
        }),
        (_("Технические настройки"), {
            "fields": ("app_mode_enabled", "maintenance_mode", "head_scripts", "body_scripts")
        }),
        (_("Почта (SMTP)"), {
            "fields": (
                "smtp_host", "smtp_port", "smtp_user", "smtp_password",
                "smtp_from_email", "smtp_use_tls", "smtp_use_ssl", "sendgrid_api_key",
            ),
            "classes": ("collapse",)
        }),
        (_("Юридическая информация"), {
            "fields": ("impressum_html", "privacy_html", "terms_html", "cookie_policy_html"),
            "classes": ("collapse",)
        }),
    )

    def has_add_permission(self, request):
        # Restrict creation when a record already exists (Singleton)
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False
