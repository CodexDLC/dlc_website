"""
Email import trigger.

Puts an ARQ task in queue if available, otherwise spawns a thread.
The actual IMAP logic lives in the ARQ worker (see NOTES.md).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings


@dataclass(frozen=True)
class MailboxCorrelationData:
    """Stable thread correlation payload for outbound/inbound email flows."""

    thread_key: str
    reply_match_token: str


class MailboxSyncAdapter(Protocol):
    """Future mailbox adapter seam for IMAP/API sync implementations."""

    def trigger_sync(self) -> dict[str, object]: ...

    def build_correlation_data(self, *, thread_key: str) -> MailboxCorrelationData: ...


def _check_arq() -> bool:
    if not (getattr(settings, "ARQ_REDIS_URL", None) or getattr(settings, "REDIS_URL", None)):
        return False
    try:
        import arq  # noqa: F401

        return True
    except ImportError:
        return False


_HAS_ARQ = _check_arq()


def trigger_email_import() -> dict:
    """
    Called from the cabinet 'Check Now' button.
    Returns immediately — import runs in background.
    """
    if _HAS_ARQ:
        from core.arq.client import arq_client

        job_id = arq_client.enqueue("import_emails_task", {})
        return {"mode": "queued", "job_id": str(job_id) if job_id else None}

    thread = threading.Thread(target=_run_import_sync, daemon=True)
    thread.start()
    return {"mode": "thread", "job_id": None}


def build_mailbox_correlation_data(*, thread_key: str) -> MailboxCorrelationData:
    """Return future-proof correlation metadata for email thread matching."""
    return MailboxCorrelationData(
        thread_key=thread_key,
        reply_match_token=thread_key,
    )


def _run_import_sync() -> None:
    """
    Stub for synchronous email import (no-ARQ fallback).
    Implement IMAP logic here or delegate to a library utility.
    See NOTES.md for the full design.
    """
    pass
