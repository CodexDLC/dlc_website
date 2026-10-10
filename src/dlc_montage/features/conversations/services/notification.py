"""
Deprecated compatibility wrapper.

Use ``features.conversations.services.alerts`` instead.
"""

from .alerts import notify_new_message

__all__ = ["notify_new_message"]
