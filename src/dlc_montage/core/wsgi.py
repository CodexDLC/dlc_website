import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dlc_montage.core.settings.dev")

application = get_wsgi_application()
