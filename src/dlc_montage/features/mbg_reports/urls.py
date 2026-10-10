from django.urls import path

from . import views

app_name = "mbg_reports"
urlpatterns = [
    path("", views.report_list, name="list"),
    path("exports/", views.export_hub, name="export_hub"),
    path("new/", views.editor, name="new"),
    path("site-options/", views.site_options, name="site_options"),
    path("site-history/", views.site_history, name="site_history"),
    path("work-item-options/", views.work_item_options, name="work_item_options"),
    path("employee-availability/", views.employee_availability, name="employee_availability"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/edit/", views.editor, name="edit"),
    path("<int:pk>/review/", views.review, name="review"),
    path("exports/weekly/", views.exports, name="exports"),
    path("exports/multi-performance/", views.multi_performance_export, name="multi_performance_export"),
    path("exports/work-completion/", views.work_completion_export, name="work_completion_export"),
    path("group/<int:group_id>/overview/", views.group_overview, name="group_overview"),
    path("group/<int:group_id>/performance/", views.performance_exports, name="performance_exports"),
    path("site/<int:site_id>/performance/", views.site_performance_export, name="site_performance_export"),
    path("group/<int:group_id>/final-hours/", views.final_hours_export, name="final_hours_export"),
    path("exports/<int:pk>/", views.download, name="download"),
    path("exports/batch-settlement/", views.batch_settlement_report, name="batch_settlement_report"),
    path("exports/master-excel/", views.master_excel_download, name="master_excel_download"),
    path("exports/google-sync/", views.google_sheets_sync, name="google_sheets_sync"),
    path("site/<int:site_id>/payment/", views.site_payment_toggle, name="site_payment_toggle"),
    path("performance/<int:pk>/download/", views.performance_download, name="performance_download"),
    path("final-hours/<int:pk>/download/", views.final_hours_download, name="final_hours_download"),
]
