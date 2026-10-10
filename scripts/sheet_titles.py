"""Shared short names for Standort worksheets."""

import re

INVALID_SHEET_CHARACTERS = re.compile(r"[\\/*?:\[\]]")
STREET_AND_NUMBER = re.compile(r"^(.+?)\s+(\d+[A-Za-z]?)$")


def legacy_sheet_title(name):
    """Return the worksheet name used before short Standort titles."""
    clean = INVALID_SHEET_CHARACTERS.sub("-", str(name)).strip()
    return clean[:31] or "Standort"


def short_sheet_title(name):
    """Abbreviate a street to its initials and keep the full house number."""
    clean = INVALID_SHEET_CHARACTERS.sub("-", str(name)).strip()
    match = STREET_AND_NUMBER.fullmatch(clean)
    if not match:
        return clean[:31] or "Standort"
    street, house = match.groups()
    words = [word for word in re.split(r"\s+", street) if word]
    if len(words) >= 2:
        initials = "".join(word[0].upper() for word in words[:2])
    elif words:
        word = words[0]
        initials = word[0].upper() + ("R" if word.casefold().endswith("ring") else "")
    else:
        return clean[:31] or "Standort"
    return f"{initials} {house.upper()}"[:31]


def assign_site_sheet_titles(sites, reserved=()):
    """Assign stable titles, suffixing abbreviation collisions by site ID."""
    used = {title.casefold() for title in reserved}
    assigned = {}
    for site_id, name in sorted(sites, key=lambda item: (str(item[1]).casefold(), item[0])):
        base = short_sheet_title(name)
        candidate = base
        number = 2
        while candidate.casefold() in used:
            suffix = f"_{number}"
            candidate = f"{base[:31 - len(suffix)]}{suffix}"
            number += 1
        assigned[site_id] = candidate
        used.add(candidate.casefold())
    return assigned


def match_existing_worksheet(worksheets, short_title, full_name):
    """Find a worksheet by new or legacy title and rename it without replacing it."""
    by_title = {worksheet.title.casefold(): worksheet for worksheet in worksheets}
    current = by_title.get(short_title.casefold())
    old_title = legacy_sheet_title(full_name)
    legacy = by_title.get(old_title.casefold())
    compact = by_title.get(short_title.replace(" ", "", 1).casefold())
    matches = []
    for candidate in (current, legacy, compact):
        if candidate is not None and all(candidate is not match for match in matches):
            matches.append(candidate)
    if len(matches) > 1:
        raise ValueError(f"Both current and legacy worksheets exist for {full_name}")
    worksheet = matches[0] if matches else None
    if worksheet and worksheet.title != short_title:
        worksheet.update_title(short_title)
    return worksheet
