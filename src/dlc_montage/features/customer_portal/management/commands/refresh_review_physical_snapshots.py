"""Обновить физические единицы только ожидающих решения приёмок."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from features.customer_portal.models import SiteReview
from features.customer_portal.services import refresh_pending_review_snapshot
from features.internal_time.policies import is_manager


class Command(BaseCommand):
    help = "Preview customer physical snapshots; --apply refreshes undecided submitted reviews."

    def add_arguments(self, parser):
        parser.add_argument("--actor", required=True)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        actor = get_user_model().objects.filter(username=options["actor"], is_active=True).first()
        if actor is None or not is_manager(actor):
            raise CommandError("An active manager actor is required.")
        changed = 0
        try:
            with transaction.atomic():
                for review in SiteReview.objects.filter(status="submitted", item_decisions={}).order_by("pk"):
                    old = review.work_snapshot
                    updated = refresh_pending_review_snapshot(actor=actor, review=review)
                    changed += old != updated.work_snapshot
                if not options["apply"]:
                    transaction.set_rollback(True)
        except Exception as error:
            raise CommandError(str(error)) from error
        mode = "Updated" if options["apply"] else "Would update (dry run)"
        self.stdout.write(f"{mode}: {changed} reviews.")
