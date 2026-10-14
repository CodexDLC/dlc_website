"""Internal-only photo upload authorization shared by services and HTTP views."""

from features.internal_time.policies import can_report, is_manager
from features.projects.policies import can_use_files


def can_upload_site_photos(actor, site):
    """Customer project-management membership never grants photo upload access."""
    return bool(
        actor.is_authenticated
        and actor.is_active
        and (is_manager(actor) or can_report(actor))
        and can_use_files(actor, site.group)
        and site.is_active
        and site.group.status == "active"
    )
