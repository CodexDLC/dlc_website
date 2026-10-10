"""Проверка содержимого и запись приватных вложений."""

from pathlib import Path

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from PIL import Image, UnidentifiedImageError

from features.internal_time.policies import is_manager
from features.projects.models import ProjectGroup
from features.projects.policies import can_use_files

from .models import ProjectFile


def validate_upload(upload, kind):
    """Разрешить только проверяемые растровые изображения и PDF до 20 МБ."""
    if not upload.size or upload.size > 20 * 1024 * 1024:
        raise ValidationError(_("Файл должен быть непустым и не больше 20 МБ."))
    suffix = Path(upload.name).suffix.lower()
    upload.seek(0)
    if suffix == ".pdf" and kind != "photo":
        valid = upload.read(5) == b"%PDF-"
        content_type = "application/pdf"
    elif suffix in (".jpg", ".jpeg", ".png", ".webp"):
        try:
            with Image.open(upload) as picture:
                valid = picture.format == {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}[suffix]
                if picture.width * picture.height > 40_000_000:
                    raise ValidationError(_("Изображение слишком большое: максимум 40 мегапикселей."))
                picture.verify()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            raise ValidationError(_("Не удалось прочитать изображение.")) from exc
        content_type = "image/" + ("jpeg" if suffix in (".jpg", ".jpeg") else suffix[1:])
    else:
        raise ValidationError(_("Разрешены JPEG, PNG, WebP и PDF; итоговое фото должно быть изображением."))
    upload.seek(0)
    if not valid:
        raise ValidationError(_("Содержимое файла не соответствует расширению."))
    return content_type


def upload_file(*, actor, group_id, upload, kind, site=None, caption=""):
    """Store a private file; remove only the new storage object on database failure."""
    group = ProjectGroup.objects.get(pk=group_id)
    if not can_use_files(actor, group):
        raise PermissionDenied
    if group.status != "active":
        raise ValidationError(_("Загрузка доступна только в активный проект."))
    if site and (site.group_id != group.pk or not site.is_active):
        raise ValidationError(_("Выберите действующий AC-объект этого проекта."))
    if kind not in dict(ProjectFile._meta.get_field("kind").choices):
        raise ValidationError(_("Выберите тип вложения."))
    content_type = validate_upload(upload, kind)
    item = ProjectFile(
        group=group,
        site=site,
        kind=kind,
        caption=caption,
        original_name=Path(upload.name).name,
        content_type=content_type,
        size=upload.size,
        uploaded_by=actor,
    )
    item.file = upload
    item.full_clean()
    try:
        with transaction.atomic():
            item.save()
    except Exception:
        if item.file and item.file._committed:
            item.file.storage.delete(item.file.name)
        raise
    return item


@transaction.atomic
def set_publicity(*, actor, file_id, public):
    if not is_manager(actor):
        raise PermissionDenied
    item = ProjectFile.objects.select_for_update().get(pk=file_id)
    if public and item.kind != "photo":
        raise ValidationError(_("Для будущего сайта можно отметить только итоговую фотографию."))
    item.is_public = public
    item.save(update_fields=["is_public"])
    return item
