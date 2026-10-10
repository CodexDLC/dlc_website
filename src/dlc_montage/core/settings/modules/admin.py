import os
from pathlib import Path

# Root of Django project: src/backend_django
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
_PROJECT_NAME = os.environ.get("PROJECT_NAME", BASE_DIR.name)

UNFOLD = {
    "SITE_TITLE": os.environ.get("ADMIN_SITE_TITLE", f"{_PROJECT_NAME.replace('_', ' ').title()} Admin"),
    "SITE_HEADER": os.environ.get("ADMIN_SITE_HEADER", _PROJECT_NAME.replace("_", " ").title()),
    "SITE_SYMBOL": "dashboard",
    "COLORS": {
        "primary": {
            "50": "239, 246, 255",
            "100": "219, 234, 254",
            "200": "191, 219, 254",
            "300": "147, 197, 253",
            "400": "96, 165, 250",
            "500": "59, 130, 246",
            "600": "37, 99, 235",
            "700": "29, 78, 216",
            "800": "30, 64, 175",
            "900": "30, 58, 138",
            "950": "23, 37, 84",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Leads & Contacts",
                "items": [
                    {
                        "title": "Contact Requests",
                        "icon": "mail",
                        "link": "/admin/main/contactrequest/",
                    },
                ],
            },
            {
                "title": "System & Settings",
                "items": [
                    {
                        "title": "Site Settings",
                        "icon": "settings",
                        "link": "/admin/system/sitesettings/",
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": "Static Translations",
                        "icon": "translate",
                        "link": "/admin/system/statictranslation/",
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": "SEO Pages",
                        "icon": "search",
                        "link": "/admin/system/staticpageseo/",
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": "/admin/auth/user/",
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
        ],
    },
}
