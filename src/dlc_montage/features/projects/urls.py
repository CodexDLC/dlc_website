from django.urls import path

from . import views

app_name = "projects"
urlpatterns = [
    path("choices/groups/", views.group_choices, name="group_choices"),
    path("choices/sites/", views.site_choices, name="site_choices"),
    path("", views.group_list, name="list"),
    path("new/", views.group_edit, name="new"),
    path("<int:pk>/", views.group_detail, name="detail"),
    path("<int:pk>/edit/", views.group_edit, name="edit"),
    path("<int:group_id>/objects/new/", views.object_edit, name="object_new"),
    path("<int:group_id>/objects/<int:pk>/overview/", views.site_detail, name="site_detail"),
    path("<int:group_id>/objects/<int:site_id>/work-items/new/", views.work_item_edit, name="work_item_new"),
    path(
        "<int:group_id>/objects/<int:site_id>/work-items/typical/",
        views.typical_work_plan, name="typical_work_plan",
    ),
    path("<int:group_id>/objects/<int:site_id>/work-items/<int:pk>/", views.work_item_edit, name="work_item_edit"),
    path(
        "<int:group_id>/objects/<int:site_id>/work-items/<int:pk>/lifecycle/",
        views.work_item_lifecycle, name="work_item_lifecycle",
    ),
    path("<int:group_id>/objects/<int:pk>/status/", views.site_status, name="site_status"),
    path("<int:group_id>/objects/<int:pk>/", views.object_edit, name="object_edit"),
    path("clients/", views.clients, name="clients"),
    path("clients/<int:pk>/", views.clients, name="client_edit"),
]
