from django.urls import path

from . import photo_views

app_name = "site_photos"

urlpatterns = [
    path("<int:site_id>/", photo_views.gallery, name="gallery"),
    path("<int:site_id>/refresh/", photo_views.refresh, name="refresh"),
    path("<int:site_id>/upload/", photo_views.upload, name="upload"),
    path("<int:site_id>/archive/", photo_views.archive, name="archive"),
    path("<int:site_id>/<int:photo_id>/thumbnail/", photo_views.thumbnail, name="thumbnail"),
    path("<int:site_id>/<int:photo_id>/", photo_views.image, name="image"),
]
