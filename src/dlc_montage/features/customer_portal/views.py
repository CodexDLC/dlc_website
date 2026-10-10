"""HTTP-адаптеры клиентского кабинета; правила остаются в сервисах."""

from dataclasses import replace
from datetime import date

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from features.internal_time.policies import is_manager
from features.project_media.models import ProjectFile
from features.project_media.views import file_response
from features.projects.forms import TypicalPlanForm
from features.projects.read_models import typical_plan_preview
from features.projects.typical_plan import build_typical_plan

from .exports import (
    group_timesheet_workbook,
    group_workbook,
    site_timesheet_workbook,
    site_workbook,
)
from .forms import CustomerGroupForm, CustomerPdfForm, CustomerSiteForm, ManualItemForm, MembershipForm
from .models import ClientMembership, CustomerAuditEvent, PlanProposal, SiteReview
from .policies import membership_for, require_customer_group, require_customer_site
from .selectors import (
    attach_site_plan_progress,
    customer_documents_context,
    customer_site_detail,
    filtered_groups_for_actor,
    filtered_sites_for_actor,
    get_cached_photo_summary,
    groups_for_actor,
    sites_for_actor,
    works_journal_days,
)
from .services import (
    change_account_password,
    decide_review,
    grant_membership,
    propose_manual_item,
    propose_plan,
    review_plan,
    save_customer_group,
    save_customer_site,
    set_customer_file_visibility,
    submit_for_review,
    upload_customer_pdf,
)


def _parse_iso_week(year_param, week_param):
    """Корректно распарсить и провалидировать ISO-год и номер недели."""
    if not year_param and not week_param:
        return None, None
    if not year_param or not week_param:
        raise ValidationError(_("Jahr und Kalenderwoche müssen gemeinsam angegeben werden."))
    try:
        year = int(year_param)
        week = int(week_param)
        if not (1900 <= year <= 2100) or not (1 <= week <= 53):
            raise ValueError
        date.fromisocalendar(year, week, 1)
    except (ValueError, TypeError):
        raise ValidationError(_("Ungültige Kalenderwoche oder ungültiges Jahr.")) from None
    return year, week


def _require_portal(actor):
    if not is_manager(actor) and membership_for(actor) is None:
        raise PermissionDenied


@login_required
@require_http_methods(["GET", "POST"])
def account(request):
    """Display the signed-in account and change only its password."""
    _require_portal(request.user)
    request.cabinet_module = "customer"
    form = PasswordChangeForm(request.user, request.POST if request.method == "POST" else None)
    form.fields["old_password"].label = _("Aktuelles Passwort")
    form.fields["new_password1"].label = _("Neues Passwort")
    form.fields["new_password2"].label = _("Neues Passwort bestätigen")
    if request.method == "POST" and form.is_valid():
        user = change_account_password(actor=request.user, password=form.cleaned_data["new_password1"])
        update_session_auth_hash(request, user)
        messages.success(request, _("Ihr Passwort wurde geändert."))
        return redirect("customer_portal:account")
    return render(request, "customer_portal/account.html", {"account_user": request.user, "form": form})


def _scope_id_param(request, key):
    """Проверить идентификатор фильтра до передачи в ORM."""
    value = request.GET.get(key, "").strip()
    if not value:
        return ""
    try:
        number = int(value)
    except ValueError:
        raise Http404(_("Некорректный фильтр.")) from None
    if not 0 < number < 2**63:
        raise Http404(_("Некорректный фильтр."))
    return str(number)


@login_required
def home(request):
    """Список только назначенных Anlagen с адаптивными карточками и пагинацией 20."""
    _require_portal(request.user)
    request.cabinet_module = "customer"
    q = request.GET.get("q", "").strip()[:100]
    status = request.GET.get("status", "active").strip()
    if status not in {"active", "completed", "all"}:
        status = "active"
    direction = request.GET.get("type", "").strip()
    if direction not in {"ac", "dc", "all"}:
        direction = ""

    groups_qs = filtered_groups_for_actor(request.user, search=q, status=status, direction=direction)
    page_obj = Paginator(groups_qs, 20).get_page(request.GET.get("page"))

    pending = (
        PlanProposal.objects.filter(status="pending").select_related("site__group") if is_manager(request.user) else ()
    )
    return render(
        request,
        "customer_portal/home.html",
        {
            "groups": page_obj,
            "groups_page": page_obj,
            "query": q,
            "status": status,
            "direction": direction,
            "manager": is_manager(request.user),
            "pending_proposals": pending,
            "membership": membership_for(request.user),
        },
    )


@login_required
def objects(request):
    """Поиск Standorte строго внутри разрешённого набора, пагинация 20, фильтры и сортировка."""
    _require_portal(request.user)
    request.cabinet_module = "customer"
    query = request.GET.get("q", "").strip()[:100]
    group_id = _scope_id_param(request, "group")
    status = request.GET.get("status", "non_completed").strip()
    if status not in {"non_completed", "completed", "all", "not_started", "started"}:
        status = "non_completed"
    sort = request.GET.get("sort", "activity").strip()
    if sort not in {"activity", "name"}:
        sort = "activity"

    sites_qs = filtered_sites_for_actor(request.user, search=query, group_id=group_id, status=status, sort=sort)
    page_obj = Paginator(sites_qs, 20).get_page(request.GET.get("page"))
    for s in page_obj:
        s.cached_photo_summary = get_cached_photo_summary(s)
    attach_site_plan_progress(page_obj.object_list)

    selected_group = None
    if group_id:
        selected_group = groups_for_actor(request.user).filter(pk=group_id).first()

    return render(
        request,
        "customer_portal/objects.html",
        {
            "sites": page_obj,
            "sites_page": page_obj,
            "query": query,
            "group_id": group_id,
            "selected_group": selected_group,
            "status": status,
            "sort": sort,
            "groups": groups_for_actor(request.user),
        },
    )


@login_required
def site_photo(request, site_id, filename):
    """Безопасное проксирование фотофиксации объекта из Nextcloud."""
    _require_portal(request.user)
    site = get_object_or_404(sites_for_actor(request.user), pk=site_id)
    require_customer_site(request.user, site)

    clean_filename = filename.strip()
    if not clean_filename or "/" in clean_filename or "\\" in clean_filename or ".." in clean_filename:
        raise Http404(_("Ungültiger Dateiname."))

    from features.integrations.nextcloud.client import NextcloudWebDAVError
    from features.integrations.nextcloud.services import fetch_site_photo

    try:
        data, mime_type = fetch_site_photo(site=site, filename=clean_filename)
    except FileNotFoundError:
        raise Http404(_("Foto nicht gefunden.")) from None
    except ValueError:
        return HttpResponseBadRequest(_("Ungültiges Dateiformat oder Inhalt."))
    except NextcloudWebDAVError:
        return HttpResponse("Fotospeicher vorübergehend nicht erreichbar.", status=502)

    response = HttpResponse(data, content_type=mime_type)
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
def works(request):
    """Журнал выполненных работ по уникальным дням с карточками Standorte."""
    _require_portal(request.user)
    request.cabinet_module = "customer"

    group_id = _scope_id_param(request, "group")
    site_id = _scope_id_param(request, "site")
    from_str = request.GET.get("from", "").strip()
    to_str = request.GET.get("to", "").strip()

    date_from = None
    date_to = None
    date_error = None
    if from_str:
        try:
            date_from = date.fromisoformat(from_str)
        except ValueError:
            date_error = _("Неверный формат начальной даты.")
    if to_str:
        try:
            date_to = date.fromisoformat(to_str)
        except ValueError:
            date_error = _("Неверный формат конечной даты.")

    days_page, day_groups = works_journal_days(
        request.user,
        group_id=group_id,
        site_id=site_id,
        date_from=date_from,
        date_to=date_to,
        page=request.GET.get("page", 1),
        per_page=7,
    )

    allowed_groups = list(groups_for_actor(request.user))
    allowed_sites = list(sites_for_actor(request.user).select_related("group"))

    return render(
        request,
        "customer_portal/works.html",
        {
            "days_page": days_page,
            "day_groups": day_groups,
            "group_id": group_id,
            "site_id": site_id,
            "from_str": from_str,
            "to_str": to_str,
            "date_error": date_error,
            "allowed_groups": allowed_groups,
            "allowed_sites": allowed_sites,
        },
    )


@login_required
def reviews(request):
    """Очередь и история проверок с карточками по 20 на страницу."""
    _require_portal(request.user)
    request.cabinet_module = "customer"
    queryset = (
        SiteReview.objects.filter(site__in=sites_for_actor(request.user))
        .select_related("site", "site__group")
        .order_by("-submitted_at", "-pk")
    )
    page_obj = Paginator(queryset, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "customer_portal/reviews.html",
        {
            "reviews_page": page_obj,
            "reviews": page_obj,
        },
    )


@login_required
def documents(request):
    """Раздел документов: выгрузка актов, табелей и PDF с раздельной пагинацией по 20."""
    _require_portal(request.user)
    request.cabinet_module = "customer"

    q_all = request.GET.get("q", "").strip()[:100]
    q_group = request.GET.get("q_group", "").strip()[:100]
    q_pdf = request.GET.get("q_pdf", "").strip()[:100]
    if q_all and not q_group and not q_pdf:
        q_group = q_all
        q_pdf = q_all

    page_groups = request.GET.get("page_groups", 1)
    page_pdf = request.GET.get("page_pdf", 1)

    context = customer_documents_context(
        request.user,
        search_group=q_group,
        search_pdf=q_pdf,
        page_groups=page_groups,
        page_pdf=page_pdf,
        per_page=20,
    )
    context.update(
        {
            "q": q_all,
            "q_group": q_group,
            "q_pdf": q_pdf,
            "page_groups": page_groups,
            "page_pdf": page_pdf,
            "can_manage_settlement": False,
        }
    )
    return render(request, "customer_portal/unified_documents.html", context)


@login_required
def audit(request):
    """Показать предметный аудит своей компании без событий выдачи доступа."""
    _require_portal(request.user)
    request.cabinet_module = "customer"
    queryset = CustomerAuditEvent.objects.select_related("actor", "client")
    if not is_manager(request.user):
        queryset = queryset.filter(client_id=membership_for(request.user).client_id).exclude(action="membership_saved")
    return render(
        request,
        "customer_portal/audit.html",
        {
            "events": Paginator(queryset, 100).get_page(request.GET.get("page")),
        },
    )


@login_required
def group_detail(request, group_id):
    """Карточка Anlage без внутренних финансовых полей."""
    group = get_object_or_404(groups_for_actor(request.user), pk=group_id)
    request.cabinet_module = "customer"
    files = ProjectFile.objects.filter(group=group, customer_visible=True, content_type="application/pdf")
    admin_files = (
        ProjectFile.objects.filter(group=group, content_type="application/pdf") if is_manager(request.user) else ()
    )
    return render(
        request,
        "customer_portal/group.html",
        {
            "group": group,
            "sites": group.ac_objects.all(),
            "files": files,
            "admin_files": admin_files,
            "manager": is_manager(request.user),
            "membership": membership_for(request.user),
        },
    )


@login_required
def site_detail(request, site_id):
    """План, подтверждённый объём, дневная работа и отдельная приёмка."""
    site = get_object_or_404(sites_for_actor(request.user), pk=site_id)
    request.cabinet_module = "customer"
    detail = customer_site_detail(site)
    from features.integrations.nextcloud.services import get_site_photo_summary

    photo_summary = get_site_photo_summary(site)
    files = ProjectFile.objects.filter(site=site, customer_visible=True, content_type="application/pdf")

    chosen_date = request.GET.get("date", "").strip()[:10]
    if chosen_date:
        try:
            date.fromisoformat(chosen_date)
        except ValueError:
            chosen_date = None

    return render(
        request,
        "customer_portal/site.html",
        {
            "detail": detail,
            "photo_summary": photo_summary,
            "show_photos": request.GET.get("show_photos") == "1",
            "site": site,
            "files": files,
            "manager": is_manager(request.user),
            "chosen_date": chosen_date,
        },
    )


@login_required
def group_edit(request, group_id=None):
    """Клиент редактирует только разрешённые поля своей Anlage."""
    _require_portal(request.user)
    membership = membership_for(request.user)
    if is_manager(request.user) or membership is None or not membership.can_manage_projects:
        raise PermissionDenied
    group = get_object_or_404(groups_for_actor(request.user), pk=group_id) if group_id else None
    form = CustomerGroupForm(request.POST or None, instance=group)
    request.cabinet_module = "customer"
    if request.method == "POST" and form.is_valid():
        try:
            data = dict(form.cleaned_data)
            reason = data.pop("reason", "")
            saved = save_customer_group(actor=request.user, group_id=group_id, data=data, reason=reason)
            return redirect("customer_portal:group", group_id=saved.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "customer_portal/form.html",
        {
            "form": form,
            "title": _("Anlage"),
            "back": "customer_portal:home",
        },
    )


@login_required
def site_edit(request, group_id, site_id=None):
    """Клиент редактирует только адрес и номер Standort."""
    group = get_object_or_404(groups_for_actor(request.user), pk=group_id)
    require_customer_group(request.user, group, manage=True)
    site = get_object_or_404(sites_for_actor(request.user), pk=site_id, group=group) if site_id else None
    form = CustomerSiteForm(request.POST or None, instance=site)
    request.cabinet_module = "customer"
    if request.method == "POST" and form.is_valid():
        try:
            data = dict(form.cleaned_data)
            reason = data.pop("reason", "")
            saved = save_customer_site(actor=request.user, group=group, data=data, site_id=site_id, reason=reason)
            return redirect("customer_portal:site", site_id=saved.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "customer_portal/form.html",
        {
            "form": form,
            "title": _("Standort"),
            "back": "customer_portal:group",
            "back_id": group.pk,
        },
    )


@login_required
def plan_proposal(request, site_id):
    """Клиент сначала проверяет строки типового плана, затем подаёт заявку."""
    site = get_object_or_404(sites_for_actor(request.user), pk=site_id)
    if is_manager(request.user):
        raise PermissionDenied
    require_customer_group(request.user, site.group, manage=True)
    request.cabinet_module = "customer"
    form = TypicalPlanForm(request.POST or None)
    rows = ()
    if request.method == "POST" and form.is_valid():
        config = form.to_config()
        try:
            rows = typical_plan_preview(build_typical_plan(config))
        except ValidationError as exc:
            form.add_error(None, exc)
        if request.POST.get("step") == "submit" and rows:
            rows = tuple(
                replace(
                    row,
                    selected=bool(request.POST.get(f"include-{row.spec.key}")),
                    quantity=request.POST.get(f"quantity-{row.spec.key}", str(row.spec.planned_quantity)),
                )
                for row in rows
            )
            try:
                propose_plan(
                    actor=request.user,
                    site=site,
                    config=config,
                    selected={row.spec.key: row.quantity for row in rows if row.selected},
                )
                return redirect("customer_portal:site", site_id=site.pk)
            except ValidationError as exc:
                form.add_error(None, exc)
    return render(request, "customer_portal/proposal.html", {"site": site, "form": form, "rows": rows})


@login_required
def manual_item_proposal(request, site_id):
    """Клиент предлагает одну работу из каталога; права и параметры проверяет сервис."""
    site = get_object_or_404(sites_for_actor(request.user), pk=site_id)
    if is_manager(request.user):
        raise PermissionDenied
    require_customer_group(request.user, site.group, manage=True)
    request.cabinet_module = "customer"
    form = ManualItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            propose_manual_item(actor=request.user, site=site, **form.cleaned_data)
            return redirect("customer_portal:site", site_id=site.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "customer_portal/form.html",
        {"form": form, "title": _("Отдельная работа из каталога"), "back": "customer_portal:site", "back_id": site.pk},
    )


@login_required
@require_POST
def proposal_decision(request, proposal_id):
    """Однократное решение менеджера по предложенным позициям."""
    if not is_manager(request.user):
        raise PermissionDenied
    proposal = get_object_or_404(PlanProposal.objects.select_related("site"), pk=proposal_id)
    if request.POST.get("decision") not in {"approve", "reject"}:
        raise PermissionDenied
    try:
        review_plan(
            actor=request.user,
            proposal=proposal,
            approve=request.POST.get("decision") == "approve",
            reason=request.POST.get("reason", ""),
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("customer_portal:site", site_id=proposal.site_id)


@login_required
@require_POST
def review_submit(request, site_id):
    """Администратор начинает отдельную заказческую проверку."""
    site = get_object_or_404(sites_for_actor(request.user), pk=site_id)
    try:
        submit_for_review(actor=request.user, site=site)
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("customer_portal:site", site_id=site_id)


@login_required
@require_POST
def review_decision(request, site_id):
    """Заказчик подтверждает отсутствие замечаний или возвращает с причиной."""
    site = get_object_or_404(sites_for_actor(request.user), pk=site_id)
    if request.POST.get("decision") not in {"accept", "return"}:
        raise PermissionDenied
    try:
        decide_review(
            actor=request.user,
            site=site,
            accept=request.POST.get("decision") == "accept",
            reason=request.POST.get("reason", ""),
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("customer_portal:site", site_id=site_id)


@login_required
def file_upload(request, group_id):
    """Прикрепить приватный PDF к своей Anlage или Standort."""
    group = get_object_or_404(groups_for_actor(request.user), pk=group_id)
    require_customer_group(request.user, group, manage=True)
    form = CustomerPdfForm(request.POST or None, request.FILES or None, group=group)
    request.cabinet_module = "customer"
    if request.method == "POST" and form.is_valid():
        try:
            upload_customer_pdf(
                actor=request.user,
                group=group,
                upload=form.cleaned_data["file"],
                site=form.cleaned_data["site"],
                caption=form.cleaned_data["caption"],
            )
            return redirect("customer_portal:group", group_id=group.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "customer_portal/form.html",
        {
            "form": form,
            "title": _("PDF-Dokument"),
            "back": "customer_portal:group",
            "back_id": group.pk,
        },
    )


@login_required
def file_download(request, file_id):
    """Отдать лишь явно открытый PDF своей компании."""
    item = get_object_or_404(
        ProjectFile.objects.select_related("group"),
        pk=file_id,
        customer_visible=True,
        content_type="application/pdf",
        group__in=groups_for_actor(request.user),
    )
    return file_response(item, as_attachment=True)


@login_required
@require_POST
def file_visibility(request, file_id):
    """Ручное открытие существующего документа клиенту менеджером."""
    if not is_manager(request.user):
        raise PermissionDenied
    item = get_object_or_404(ProjectFile, pk=file_id)
    try:
        set_customer_file_visibility(
            actor=request.user,
            item=item,
            visible=request.POST.get("visible") == "1",
            reason=request.POST.get("reason", ""),
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("customer_portal:group", group_id=item.group_id)


@login_required
def accepted_work_xlsx(request, site_id):
    """Скачать безценовой XLSX Standort из клиентской проекции."""
    _require_portal(request.user)
    site = get_object_or_404(sites_for_actor(request.user), pk=site_id)
    try:
        iso_year, iso_week = _parse_iso_week(request.GET.get("year"), request.GET.get("week"))
    except ValidationError:
        return HttpResponseBadRequest(_("Ungültige Kalenderwoche oder ungültiges Jahr."))
    data = site_workbook(site, iso_year=iso_year, iso_week=iso_week)
    response = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    if iso_year and iso_week:
        fname = f"standort-{site.pk}-arbeiten-KW{iso_week:02d}-{iso_year}.xlsx"
    else:
        fname = f"standort-{site.pk}-arbeiten.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{fname}"'
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def group_work_xlsx(request, group_id):
    """Скачать обзор Anlage с отдельными безценовыми листами Standort."""
    _require_portal(request.user)
    group = get_object_or_404(groups_for_actor(request.user), pk=group_id)
    data = group_workbook(group)
    response = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="anlage-{group.pk}-arbeiten.xlsx"'
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def site_timesheet_xlsx(request, site_id):
    """Скачать табель MBG одного Standort с фактическими человеко-часами."""
    _require_portal(request.user)
    site = get_object_or_404(sites_for_actor(request.user), pk=site_id)
    try:
        iso_year, iso_week = _parse_iso_week(request.GET.get("year"), request.GET.get("week"))
    except ValidationError:
        return HttpResponseBadRequest(_("Ungültige Kalenderwoche oder ungültiges Jahr."))
    data = site_timesheet_workbook(site, iso_year=iso_year, iso_week=iso_week)
    response = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    if iso_year and iso_week:
        fname = f"standort-{site.pk}-stundennachweis-KW{iso_week:02d}-{iso_year}.xlsx"
    else:
        fname = f"standort-{site.pk}-stundennachweis.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{fname}"'
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def group_timesheet_xlsx(request, group_id):
    """Скачать табель MBG всей Anlage со сводным листом и листами Standorte."""
    _require_portal(request.user)
    group = get_object_or_404(groups_for_actor(request.user), pk=group_id)
    try:
        iso_year, iso_week = _parse_iso_week(request.GET.get("year"), request.GET.get("week"))
    except ValidationError:
        return HttpResponseBadRequest(_("Ungültige Kalenderwoche oder ungültiges Jahr."))
    data = group_timesheet_workbook(group, iso_year=iso_year, iso_week=iso_week)
    response = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    if iso_year and iso_week:
        fname = f"anlage-{group.pk}-stundennachweis-KW{iso_week:02d}-{iso_year}.xlsx"
    else:
        fname = f"anlage-{group.pk}-stundennachweis.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{fname}"'
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def memberships(request):
    """Менеджер видит явные назначения компаний пользователям."""
    if not is_manager(request.user):
        raise PermissionDenied
    request.cabinet_module = "customer"
    return render(
        request,
        "customer_portal/memberships.html",
        {
            "memberships": ClientMembership.objects.select_related("user", "client", "granted_by"),
        },
    )


@login_required
def membership_edit(request):
    """Менеджер вручную сохраняет компанию и право создавать проекты."""
    if not is_manager(request.user):
        raise PermissionDenied
    request.cabinet_module = "customer"
    form = MembershipForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            grant_membership(actor=request.user, **form.cleaned_data)
            return redirect("customer_portal:memberships")
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "customer_portal/form.html",
        {
            "form": form,
            "title": _("Доступ заказчика"),
            "back": "customer_portal:memberships",
        },
    )
