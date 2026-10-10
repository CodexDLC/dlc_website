"""Управление командами в кабинете."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from features.internal_time.policies import can_report, is_manager
from features.internal_time.selectors import available_teams

from .forms import TeamForm
from .services import save_team


@login_required
@require_http_methods(["GET", "POST"])
def teams(request, pk=None):
    if not can_report(request.user):
        raise PermissionDenied
    request.cabinet_module = "staff"
    team = get_object_or_404(available_teams(request.user), pk=pk) if pk else None
    initial = (
        {
            "name": team.name,
            "owner": team.owner_id,
            "members": list(team.memberships.values_list("employee_id", flat=True)),
        }
        if team
        else {}
    )
    form = TeamForm(request.POST or None, user=request.user, team=team, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            save_team(actor=request.user, team_id=pk, **form.cleaned_data)
            return redirect("crews:list")
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "crews/teams.html",
        {"form": form, "team": team, "teams": available_teams(request.user), "manager": is_manager(request.user)},
    )
