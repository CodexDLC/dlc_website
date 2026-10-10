"""Изолированные URL клиентского кабинета."""

from django.urls import path

from . import views

app_name = "customer_portal"

urlpatterns = [
    path("", views.home, name="home"),
    path("account/", views.account, name="account"),
    path("objects/", views.objects, name="objects"),
    path("works/", views.works, name="works"),
    path("reviews/", views.reviews, name="reviews"),
    path("documents/", views.documents, name="documents"),
    path("audit/", views.audit, name="audit"),
    path("groups/new/", views.group_edit, name="group_new"),
    path("groups/<int:group_id>/", views.group_detail, name="group"),
    path("groups/<int:group_id>/edit/", views.group_edit, name="group_edit"),
    path("groups/<int:group_id>/sites/new/", views.site_edit, name="site_new"),
    path("groups/<int:group_id>/files/new/", views.file_upload, name="file_upload"),
    path("groups/<int:group_id>/accepted-work.xlsx", views.group_work_xlsx, name="group_work_xlsx"),
    path("groups/<int:group_id>/timesheet.xlsx", views.group_timesheet_xlsx, name="group_timesheet_xlsx"),
    path("sites/<int:site_id>/", views.site_detail, name="site"),
    path("sites/<int:site_id>/photos/<str:filename>", views.site_photo, name="site_photo"),
    path("sites/<int:site_id>/edit/<int:group_id>/", views.site_edit, name="site_edit"),
    path("sites/<int:site_id>/plan/propose/", views.plan_proposal, name="plan_proposal"),
    path("sites/<int:site_id>/plan/propose-item/", views.manual_item_proposal, name="manual_item_proposal"),
    path("sites/<int:site_id>/review/submit/", views.review_submit, name="review_submit"),
    path("sites/<int:site_id>/review/decide/", views.review_decision, name="review_decision"),
    path("sites/<int:site_id>/accepted-work.xlsx", views.accepted_work_xlsx, name="accepted_work_xlsx"),
    path("sites/<int:site_id>/timesheet.xlsx", views.site_timesheet_xlsx, name="site_timesheet_xlsx"),
    path("proposals/<int:proposal_id>/decide/", views.proposal_decision, name="proposal_decision"),
    path("files/<int:file_id>/download/", views.file_download, name="file_download"),
    path("files/<int:file_id>/visibility/", views.file_visibility, name="file_visibility"),
    path("memberships/", views.memberships, name="memberships"),
    path("memberships/edit/", views.membership_edit, name="membership_edit"),
]
