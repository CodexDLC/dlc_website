"""Prepare public page copy for the selected supported language."""

from . import content


def get_public_copy(language: str) -> dict[str, object]:
    """Return the selected copy without changing the shared content definitions."""
    return {"brand": content.COMPANY_NAME, **content.PUBLIC_COPY[language]}
