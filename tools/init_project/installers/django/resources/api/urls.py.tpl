"""
{{PROJECT_NAME}} — API Configuration (Django Ninja).

Versioned API routers. Bot and external clients use these endpoints.
Docs: /api/docs
"""

from ninja import NinjaAPI, Router

api = NinjaAPI(
    title="{{PROJECT_NAME}} API",
    version="1.0.0",
)

# ── v1 ──
v1 = Router()


@v1.get("/health")
def health(request):
    """Health check endpoint."""
    return {"status": "ok"}


api.add_router("/v1/", v1)
