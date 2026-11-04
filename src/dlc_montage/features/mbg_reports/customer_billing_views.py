"""Financial customer billing pages."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from features.projects.models import AcObject

from .customer_billing_forms import CustomerPackageForm
from .customer_billing_selectors import customer_billing_summary
from .customer_billing_services import prepare_customer_packages, save_customer_package
from .models import CustomerWorkPackage
from .policies import can_export_reports


def _site(request, site_id):
    if not can_export_reports(request.user):
        raise PermissionDenied
    request.cabinet_module = "administration"
    return get_object_or_404(AcObject.objects.select_related("group"), pk=site_id)


@login_required
@require_http_methods(["GET", "POST"])
def customer_billing(request, site_id):
    site = _site(request, site_id)
    if request.method == "POST":
        if request.POST.get("action") != "prepare":
            raise PermissionDenied
        try:
            prepare_customer_packages(actor=request.user, site=site)
            messages.success(request, "Eindeutige Zuordnungen wurden vorbereitet.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        return redirect("mbg_reports:customer_billing", site_id=site.pk)
    return render(
        request, "mbg_reports/customer_billing.html", {"site": site, "summary": customer_billing_summary(site)}
    )


@login_required
@require_http_methods(["GET", "POST"])
def customer_package(request, site_id, pk=None):
    site = _site(request, site_id)
    package = get_object_or_404(CustomerWorkPackage, pk=pk, site=site) if pk else None
    form = CustomerPackageForm(request.POST or None, site=site, instance=package)
    if request.method == "POST" and form.is_valid():
        try:
            save_customer_package(actor=request.user, site=site, pk=pk, **form.cleaned_data)
            return redirect("mbg_reports:customer_billing", site_id=site.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "mbg_reports/customer_package_form.html", {"site": site, "package": package, "form": form})
