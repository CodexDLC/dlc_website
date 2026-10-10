"""Подготовить переводы исторических названий отдельно от исходных снимков."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from features.customer_portal.models import SiteReview
from features.internal_time.policies import is_manager
from features.mbg_reports.models import MbgReportRevision
from features.projects.models import SiteWorkItem
from features.work_catalog.localization import WorkNameResolver
from features.work_catalog.models import WorkDescriptionTranslation


class Command(BaseCommand):
    help = "Prepare database-owned bilingual work names; accepted reports remain immutable."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--actor")

    def handle(self, *args, **options):
        from features.work_catalog.description_translations import PHRASES, translate_description

        if options["apply"]:
            actor = get_user_model().objects.filter(username=options["actor"]).first()
            if actor is None or not is_manager(actor):
                raise CommandError("Applying translations requires --actor naming a manager.")
        titles = set(SiteWorkItem.objects.values_list("label", flat=True))
        for snapshot in MbgReportRevision.objects.values_list("snapshot", flat=True):
            for entry in snapshot.get("entries", []):
                titles.update(
                    str(entry.get(field) or "").strip()
                    for field in ("description", "custom_description", "route", "cable_type")
                )
        for rows in SiteReview.objects.values_list("work_snapshot", flat=True):
            for row in rows:
                titles.update(str(row.get(field) or "").strip() for field in ("name", "route", "cable_type"))
        titles.discard("")
        titles.update(PHRASES)
        resolver = WorkNameResolver()
        existing = set(WorkDescriptionTranslation.objects.values_list("original", flat=True))
        prepared, missing = [], 0
        for title in sorted(titles - existing):
            de, ru = resolver.pair(title)
            translated = PHRASES.get(title) or translate_description(title)
            if translated is not None:
                ru = translated
            if translated is None and title not in resolver.names:
                missing += 1
                continue
            prepared.append(WorkDescriptionTranslation(original=title, name_de=de, name_ru=ru))
        if options["apply"]:
            with transaction.atomic():
                WorkDescriptionTranslation.objects.bulk_create(prepared)
        self.stdout.write(
            f"Titles: {len(titles)}; existing: {len(existing)}; prepared: {len(prepared)}; "
            f"unresolved: {missing}; applied: {bool(options['apply'])}"
        )
