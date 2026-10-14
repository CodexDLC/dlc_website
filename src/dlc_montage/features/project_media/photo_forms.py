"""Validate a bounded set of site photos before the first storage write."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import get_language

from .services import validate_upload


class MultiplePhotoInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiplePhotoField(forms.FileField):
    def clean(self, data, initial=None):
        if not data:
            return super().clean(None, initial)
        uploads = data if isinstance(data, (list, tuple)) else [data]
        if len(uploads) > 100:
            message = (
                "Выберите не больше 100 фотографий за одну загрузку."
                if (get_language() or "").startswith("ru")
                else "Wählen Sie höchstens 100 Fotos pro Upload."
            )
            raise ValidationError(message)
        return [super(MultiplePhotoField, self).clean(upload, initial) for upload in uploads]


class PhotoUploadForm(forms.Form):
    photos = MultiplePhotoField(
        widget=MultiplePhotoInput(attrs={"accept": "image/jpeg,image/png,image/webp", "multiple": True}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["photos"].label = (
            "Фотографии" if (get_language() or "").startswith("ru") else "Fotos"
        )

    def clean_photos(self):
        uploads = self.cleaned_data["photos"]
        if sum(upload.size for upload in uploads) > 100 * 1024 * 1024:
            raise ValidationError(
                "Общий размер загрузки не должен превышать 100 МБ."
                if (get_language() or "").startswith("ru")
                else "Der gesamte Upload darf 100 MB nicht überschreiten."
            )
        errors = []
        for upload in uploads:
            try:
                validate_upload(upload, "photo")
            except ValidationError as error:
                errors.extend(f"{upload.name}: {message}" for message in error.messages)
        if errors:
            raise ValidationError(errors)
        return uploads
