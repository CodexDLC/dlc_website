"""Short Standort worksheet names stay consistent across report paths."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sheet_titles import assign_site_sheet_titles, match_existing_worksheet, short_sheet_title


def test_expected_site_abbreviations():
    assert short_sheet_title("Aroser Allee 175") == "AA 175"
    assert short_sheet_title("Huttwiler Weg 10A") == "HW 10A"
    assert short_sheet_title("Ragazer Str. 33") == "RS 33"
    assert short_sheet_title("Ragazer Straße 33") == "RS 33"
    assert short_sheet_title("Romanshorner Weg 206") == "RW 206"
    assert short_sheet_title("Schillerring 32") == "SR 32"


def test_collisions_use_deterministic_bounded_suffix():
    sites = [(9, "Ragazer Straße 33"), (3, "Ragazer Str. 33")]
    assert assign_site_sheet_titles(sites, reserved={"Übersicht"}) == {3: "RS 33", 9: "RS 33_2"}
    assert all(len(value) <= 31 for value in assign_site_sheet_titles(sites).values())


def test_existing_full_name_sheet_is_renamed_in_place():
    class Worksheet:
        id = 123
        title = "Aroser Allee 175"

        def update_title(self, title):
            self.title = title

    worksheet = Worksheet()
    assert match_existing_worksheet([worksheet], "AA 175", "Aroser Allee 175") is worksheet
    assert worksheet.id == 123
    assert worksheet.title == "AA 175"


def test_existing_compact_short_sheet_is_renamed_in_place():
    class Worksheet:
        id = 456
        title = "SR32"

        def update_title(self, title):
            self.title = title

    worksheet = Worksheet()
    assert match_existing_worksheet([worksheet], "SR 32", "Schillerring 32") is worksheet
    assert worksheet.id == 456
    assert worksheet.title == "SR 32"


def test_existing_short_and_full_name_sheets_are_not_merged():
    class Worksheet:
        def __init__(self, title):
            self.title = title

    with pytest.raises(ValueError, match="Both current and legacy"):
        match_existing_worksheet(
            [Worksheet("AA 175"), Worksheet("Aroser Allee 175")], "AA 175", "Aroser Allee 175"
        )
