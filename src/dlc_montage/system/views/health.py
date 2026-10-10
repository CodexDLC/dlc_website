"""Health check view for container readiness, Docker healthchecks, and load balancers."""

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from loguru import logger


def health_check(request):
    """Perform health checks on database and cache connectivity."""
    db_ok = False
    cache_ok = False
    errors = {}

    # Check Database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
            if row and row[0] == 1:
                db_ok = True
    except Exception:
        logger.warning("Healthcheck DB probe failed")
        errors["database"] = "unavailable"

    # Check Cache / Redis
    try:
        cache.set("__healthcheck__", "1", 10)
        if cache.get("__healthcheck__") == "1":
            cache_ok = True
    except Exception:
        logger.warning("Healthcheck cache probe failed")
        errors["cache"] = "unavailable"

    is_healthy = db_ok and cache_ok
    status_code = 200 if is_healthy else 503

    payload = {
        "status": "ok" if is_healthy else "error",
        "database": "ok" if db_ok else "unhealthy",
        "cache": "ok" if cache_ok else "unhealthy",
    }
    if errors:
        payload["errors"] = errors

    return JsonResponse(payload, status=status_code)
