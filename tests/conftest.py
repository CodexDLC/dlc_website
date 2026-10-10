"""Keep language-aware tests independent of preceding HTTP requests."""

import pytest
from django.conf import settings
from django.utils.translation import override


@pytest.fixture(autouse=True)
def isolated_language():
    """Each test starts in the configured language and restores it on completion."""
    with override(settings.LANGUAGE_CODE):
        yield
