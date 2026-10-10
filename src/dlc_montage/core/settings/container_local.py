"""
Local container settings for testing containerized stack over HTTP loopback.

Inherits full production configuration (PostgreSQL, Redis cached_db, ManifestStaticFilesStorage)
while permitting non-TLS cookies and disabling HTTPS redirect for local loopback ports (8000/8080).
"""

from .prod import *  # noqa: F403

# Local container loopback operates over HTTP without TLS certificates
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
LANGUAGE_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
