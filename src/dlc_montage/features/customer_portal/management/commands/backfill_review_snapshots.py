"""Подготовить состав ранее отправленных проверок без повторной отправки."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from features.customer_portal.models import SiteReview
from features.customer_portal.services import backfill_review_snapshot
from features.internal_time.policies import is_manager


class Command(BaseCommand):
    help = "Prepare work snapshots for existing submitted customer reviews."

    def add_arguments(self, parser):
        parser.add_argument("--actor", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        actor = get_user_model().objects.filter(username=options["actor"], is_active=True).first()
        if actor is None or not is_manager(actor):
            raise CommandError("An active manager actor is required.")
        prepared = empty = 0
        for review in SiteReview.objects.filter(status="submitted", work_snapshot=[]).order_by("pk"):
            review = backfill_review_snapshot(actor=actor, review=review)
            prepared += 1
            empty += not bool(review.work_snapshot)
        self.stdout.write(self.style.SUCCESS(f"Prepared {prepared} reviews; {empty} without confirmed work positions."))
