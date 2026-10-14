"""Run photo synchronization independently of the HTTP worker pool."""

import time
from pathlib import Path

from django.core.management.base import BaseCommand

from features.project_media.photo_services import process_pending_photo_syncs


class Command(BaseCommand):
    help = "Process durable site photo imports in an isolated worker."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--interval", type=float, default=5.0)
        # A non-secret liveness marker inside the isolated worker container.
        parser.add_argument("--heartbeat-file", default="/tmp/dlc-photo-worker-heartbeat")  # noqa: S108

    def handle(self, *args, **options):
        heartbeat = Path(options["heartbeat_file"])
        heartbeat.parent.mkdir(parents=True, exist_ok=True)
        while True:
            heartbeat.touch()
            processed = process_pending_photo_syncs(limit=1)
            heartbeat.touch()
            if options["once"]:
                self.stdout.write(f"Processed {processed} photo sync batch(es).")
                return
            if not processed:
                time.sleep(max(1.0, options["interval"]))
