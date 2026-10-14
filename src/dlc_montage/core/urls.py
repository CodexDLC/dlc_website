from typing import Any

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from features.management_reports.views import monthly
from features.project_media.views import index as file_index
from features.projects import views as project_views
from features.staff.views import employee_edit, employee_list
from system.views.health import health_check
from system.views.indexing import robots_txt, site_sitemap
from system.views.language import switch_language

from core.sitemaps import sitemaps

# Error Handlers
handler404 = "system.views.errors.handler404"
handler500 = "system.views.errors.handler500"
handler403 = "system.views.errors.handler403"
handler400 = "system.views.errors.handler400"

# Non-prefixed patterns (API, technical files)
urlpatterns: list[Any] = [
    path("health/", health_check, name="health_check"),
    path("sitemap.xml", site_sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("i18n/setlang/", switch_language, name="set_language"),
    path("robots.txt", robots_txt),
    path("llms_de.txt", TemplateView.as_view(template_name="llms_de.txt", content_type="text/plain")),
    path("llms_en.txt", TemplateView.as_view(template_name="llms_en.txt", content_type="text/plain")),
]
urlpatterns += i18n_patterns(
    path("cabinet/demo/", include("features.demo.urls")),
    path("cabinet/customer/", include("features.customer_portal.urls")),
    path("cabinet/photos/", include("features.project_media.photo_urls")),
    path("cabinet/ac/files/", file_index, {"direction": "ac"}),
    path("cabinet/dc/files/", file_index, {"direction": "dc"}),
    path("cabinet/project-files/", include("features.project_media.urls")),
    path("cabinet/staff/hours/", monthly, name="monthly_hours"),
    path("cabinet/staff/employees/new/", employee_edit, name="staff_employee_new"),
    path("cabinet/staff/employees/<int:pk>/", employee_edit, name="staff_employee_edit"),
    path("cabinet/ac/mbg-reports/", include("features.mbg_reports.urls")),
    path("cabinet/administration/work-catalog/", include("features.work_catalog.urls")),
    path("cabinet/projects/", include("features.projects.urls")),
    path("cabinet/ac/groups/", project_views.group_list, {"direction": "ac"}),
    path("cabinet/dc/groups/", project_views.group_list, {"direction": "dc"}),
    path("cabinet/ac/objects/", project_views.object_list, name="ac_objects"),
    path("cabinet/administration/project-groups/", project_views.group_list),
    path("cabinet/administration/clients/", project_views.clients),
    path("cabinet/staff/employees/", employee_list, name="staff_employees"),
    path("cabinet/staff/time-reports/", include("features.internal_time.urls")),
    path("cabinet/staff/crews/", include("features.crews.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("cabinet/", include("cabinet.urls")),
    path("system/", include("system.urls")),
    path("conversations/", include("features.conversations.urls")),
    path("", include("features.main.urls")),
    prefix_default_language=True,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
