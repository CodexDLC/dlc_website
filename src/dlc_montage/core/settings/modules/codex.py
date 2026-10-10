import os

# ═══════════════════════════════════════════
# Authentication & django-allauth
# ═══════════════════════════════════════════

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_UNIQUE_EMAIL = True

LOGIN_URL = "/cabinet/login/"
LOGIN_REDIRECT_URL = "/cabinet/staff/time-reports/"
LOGOUT_REDIRECT_URL = "/cabinet/login/"

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

# Cabinet adapter hooks are scaffold-owned now.
# Keep commented defaults as extension points for project-specific redirects.
# ACCOUNT_ADAPTER = "cabinet.adapters.CabinetAccountAdapter"
# CABINET_DEFAULT_URL = "/cabinet/"
# CABINET_CLIENT_URL = "/cabinet/my/"
