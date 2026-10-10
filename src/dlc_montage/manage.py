#!/usr/bin/env python
"""Django management script."""

import os
import sys


def main():
    """Run administrative tasks."""
    # Ensure both src/ and src/<project>/ are on sys.path.
    # src/         → needed for DJANGO_SETTINGS_MODULE = "<project>.core.settings.*"
    # src/<project>/ → needed for LOCAL_APPS = ["core", "system", "cabinet", ...]
    project_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(project_dir)
    for path in [src_dir, project_dir]:
        if path not in sys.path:
            sys.path.insert(0, path)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dlc_montage.core.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
