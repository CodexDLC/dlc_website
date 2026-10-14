"""Authorized delivery of saved photos; web requests never contact Nextcloud."""

from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import content_disposition_header
from django.utils.translation import get_language
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from loguru import logger

from features.customer_portal.policies import membership_for, require_customer_site
from features.projects.models import AcObject
from features.projects.policies import can_view_group

from .photo_policies import can_upload_site_photos
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
            "can_upload_photo": can_upload_site_photos(request.user, site),
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
    return _image_response(
        photo.image, photo.content_type, photo.original_name, download=request.GET.get("download") == "1"
    )


def _image_response(file, content_type, filename, *, download=False):
    if settings.PHOTOS_STORAGE_BACKEND == "s3":
        url = (
            file.storage.url(
                file.name, parameters={"ResponseContentDisposition": content_disposition_header(True, filename)}
            )
            if download
            else file.url
        )
        response = redirect(url)
    else:
        try:
            response = FileResponse(
                file.open("rb"), content_type=content_type, as_attachment=download, filename=filename
            )
        except FileNotFoundError:
            raise Http404 from None
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
@require_GET
def thumbnail(request, site_id, photo_id):
    photo = get_site_photo(_authorized_site(request, site_id), photo_id)
    if photo is None or not photo.thumbnail:
        raise Http404
    return _image_response(photo.thumbnail, photo.thumbnail_content_type, "thumbnail.webp")


def _return_url(request, site):
    if membership_for(request.user):
        return reverse("customer_portal:site", args=[site.pk])
    return reverse("projects:site_detail", args=[site.group_id, site.pk])


@login_required
@require_http_methods(["GET", "POST"])
def upload(request, site_id):
    from .photo_forms import PhotoUploadForm
    from .photo_services import upload_site_photo

    site = _authorized_site(request, site_id)
    if not can_upload_site_photos(request.user, site):
        raise PermissionDenied
    request.cabinet_module = "customer" if membership_for(request.user) else "ac"
    form = PhotoUploadForm(request.POST or None, request.FILES or None)
    uploaded, errors = [], []
    if request.method == "POST" and form.is_valid():
        for file in form.cleaned_data["photos"]:
            try:
                uploaded.append(upload_site_photo(actor=request.user, site=site, upload=file))
            except ValidationError as exc:
                errors.append({"name": file.name, "message": " ".join(exc.messages)})
            except (BotoCoreError, ClientError, OSError) as exc:
                logger.bind(site_id=site.pk, error_type=type(exc).__name__).warning("Photo upload storage failed")
                message = (
                    "Не удалось сохранить фотографию. Повторите загрузку."
                    if (get_language() or "").startswith("ru")
                    else "Das Foto konnte nicht gespeichert werden. Bitte erneut hochladen."
                )
                errors.append({"name": file.name, "message": message})
        if not errors:
            return redirect(_return_url(request, site))
    return render(
        request,
        "project_media/photo_upload.html",
        {
            "site": site,
            "form": form,
            "uploaded_photos": uploaded,
            "upload_errors": errors,
            "return_url": _return_url(request, site),
        },
    )


@login_required
@require_GET
def archive(request, site_id):
    from .photo_exports import build_photo_archive

    site = _authorized_site(request, site_id)
    try:
        output = build_photo_archive(site)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect(_return_url(request, site))
    response = FileResponse(
        output, content_type="application/zip", as_attachment=True, filename=f"site-{site.pk}-photos.zip"
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
