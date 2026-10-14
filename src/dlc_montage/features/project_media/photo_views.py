"""Authorized delivery of saved photos; web requests never contact Nextcloud."""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST

from features.customer_portal.policies import membership_for, require_customer_site
from features.projects.models import AcObject
from features.projects.policies import can_view_group

from .photo_selectors import get_site_photo, get_site_photo_summary
from .photo_services import request_site_photo_sync


def _authorized_site(request, site_id):
    site = get_object_or_404(AcObject.objects.select_related("group"), pk=site_id)
    if not request.user.is_active:
        raise PermissionDenied
    if membership_for(request.user):
        require_customer_site(request.user, site)
    elif not can_view_group(request.user, site.group):
        raise PermissionDenied
    return site


def _gallery_response(request, site):
    expanded = request.GET.get("show_photos") == "1"
    summary = get_site_photo_summary(site, include_photos=expanded)
    html = render_to_string(
        "project_media/includes/site_photos.html",
        {
            "site": site,
            "photo_summary": summary,
            "show_photos": expanded,
        },
        request=request,
    )
    response = JsonResponse({"html": html, "status": summary["sync_status"], "count": summary["count"]})
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_GET
def gallery(request, site_id):
    return _gallery_response(request, _authorized_site(request, site_id))


@login_required
@require_POST
def refresh(request, site_id):
    site = _authorized_site(request, site_id)
    request_site_photo_sync(site)
    return _gallery_response(request, site)


@login_required
@require_GET
def image(request, site_id, photo_id):
    site = _authorized_site(request, site_id)
    photo = get_site_photo(site, photo_id)
    if photo is None:
        raise Http404
    if settings.PHOTOS_STORAGE_BACKEND == "s3":
        response = redirect(photo.image.url)
    else:
        try:
            response = FileResponse(photo.image.open("rb"), content_type=photo.content_type)
        except FileNotFoundError:
            raise Http404 from None
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
