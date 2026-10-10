"""Maintain reviewed Russian/German catalogs without fuzzy translation reuse.

Run with the project Python environment: ``python scripts/localization.py extract``
or ``python scripts/localization.py compile``. Extraction may create empty entries;
translate those manually before compilation.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("extract", "compile"))
    action = parser.parse_args().action
    project = Path(__file__).resolve().parents[1] / "src" / "dlc_montage"
    if action == "extract":
        sys.path[:0] = [str(project.parent), str(project)]
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dlc_montage.core.settings.dev")
        import django
        from django.core.management import call_command
        from django.core.management.commands.makemessages import Command

        django.setup()
        command = Command()
        command.msgmerge_options = [*command.msgmerge_options, "--no-fuzzy-matching"]
        os.chdir(project)
        call_command(command, locale=["de", "ru"], no_wrap=True, no_obsolete=True)
    else:
        msgfmt = shutil.which("msgfmt")
        msgattrib = shutil.which("msgattrib")
        if not msgfmt or not msgattrib:
            parser.error("GNU gettext (msgfmt and msgattrib) is required")
        for language in ("de", "ru"):
            catalog = project / "locale" / language / "LC_MESSAGES" / "django.po"
            for selection in ("--only-fuzzy", "--untranslated"):
                result = subprocess.run(  # noqa: S603 - fixed gettext executable and project catalog
                    [msgattrib, selection, "--no-obsolete", str(catalog)],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                if re.search(r'^msgid (?!"")', result.stdout, re.MULTILINE):
                    parser.error(f"{language} catalog contains {selection[2:]} entries; review translations first")
            # --check catches placeholders, plural/header errors and malformed PO.
            subprocess.run(  # noqa: S603 - fixed gettext executable and project catalog
                [msgfmt, "--check", "--check-format", "-o", str(catalog.with_suffix(".mo")), str(catalog)],
                check=True,
            )


if __name__ == "__main__":
    main()
