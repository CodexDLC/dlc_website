# ═══════════════════════════════════════════
# Application definition
# ═══════════════════════════════════════════

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
]

THIRD_PARTY_APPS = [
    # Auth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    # Admin
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "unfold.contrib.import_export",
    "unfold.contrib.guardian",
    "unfold.contrib.simple_history",
    "django_prometheus",
    "ninja",
]
THIRD_PARTY_APPS.insert(0, "modeltranslation")

# ═══════════════════════════════════════════
# Codex Library Apps
# ═══════════════════════════════════════════
CODEX_APPS = [
    "codex_django.cabinet",
]

# ═══════════════════════════════════════════
# Codex Library Settings
# ═══════════════════════════════════════════
CODEX_SITE_SETTINGS_MODEL = "system.SiteSettings"
CODEX_STATIC_TRANSLATION_MODEL = "system.StaticTranslation"
CODEX_STATIC_PAGE_SEO_MODEL = "system.StaticPageSeo"

LOCAL_APPS = [
    "core",
    "system",
    "features.main",
    "cabinet",
    "features.conversations",
    "features.staff",
    "features.projects",
    "features.crews",
    "features.internal_time",
    "features.ac_reporting",
    "features.work_catalog",
    "features.mbg_reports",
    "features.management_reports",
    "features.project_media",
    "features.customer_portal",
    "features.telegram_access",
]

INSTALLED_APPS = CODEX_APPS + THIRD_PARTY_APPS + DJANGO_APPS + LOCAL_APPS
