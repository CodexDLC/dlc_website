from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from features.internal_time.policies import is_manager
from features.projects.models import ProjectGroup
from features.projects.policies import can_use_files

from .forms import MediaFilterForm, UploadForm
from .models import ProjectFile
from .selectors import file_groups, files_for_group
from .services import set_publicity, upload_file


@login_required
def index(request, direction):
    request.cabinet_module = direction
    return render(request, "project_media/groups.html", {"groups": file_groups(request.user, direction)})


@login_required
def files(request, group_id):
    group = get_object_or_404(ProjectGroup, pk=group_id)
    if not can_use_files(request.user, group):
        raise PermissionDenied
    request.cabinet_module = "ac" if group.has_ac else "dc"
    form = UploadForm(request.POST or None, request.FILES or None, group=group)
    filter_form = MediaFilterForm(request.GET or None, group=group)
    if request.method == "POST" and form.is_valid():
        data = dict(form.cleaned_data)
        upload = data.pop("file")
        try:
            upload_file(actor=request.user, group_id=group.pk, upload=upload, **data)
            return redirect("project_media:list", group_id=group.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    filters = filter_form.cleaned_data if filter_form.is_valid() else {"kind": "", "site": ""}
    return render(
        request,
        "project_media/list.html",
        {
            "group": group,
            "form": form,
            "filter_form": filter_form,
            "files": files_for_group(group, **filters),
            "manager": is_manager(request.user),
        },
    )


def protected_file(request, pk):
    """Получить файл только после проверки доступа к его проекту."""
    item = get_object_or_404(ProjectFile.objects.select_related("group"), pk=pk)
    if not can_use_files(request.user, item.group):
        raise PermissionDenied
    return item


def file_response(item, *, as_attachment):
    """Отдать приватный файл для просмотра или скачивания без кэширования."""
    response = FileResponse(
        item.file.open("rb"),
        as_attachment=as_attachment,
        filename=item.original_name,
        content_type=item.content_type,
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "sandbox"
    return response


@login_required
@xframe_options_sameorigin
def preview(request, pk):
    item = protected_file(request, pk)
    if not item.can_preview:
        raise Http404
    return file_response(item, as_attachment=False)


@login_required
def download(request, pk):
    return file_response(protected_file(request, pk), as_attachment=True)


@login_required
@require_POST
def publicity(request, pk):
    item = get_object_or_404(ProjectFile, pk=pk)
    set_publicity(actor=request.user, file_id=item.pk, public=request.POST.get("public") == "1")
    return redirect("project_media:list", group_id=item.group_id)
