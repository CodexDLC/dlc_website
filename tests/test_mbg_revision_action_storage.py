"""Служебные отметки истории помещаются в поле и сохраняются без обрезки."""

from features.mbg_reports.models import MbgReportRevision


def test_revision_action_accepts_existing_long_markers():
    marker = "legacy_plan_confirmation"
    field = MbgReportRevision._meta.get_field("action")
    assert field.clean(marker, None) == marker
