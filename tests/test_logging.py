import os
from pathlib import Path

from core.logger import DjangoLoggingSettingsAdapter
from django.test import override_settings


def test_logging_adapter_disables_file_mode_when_requested():
    with override_settings(DEBUG=True, LOG_FILE_ENABLED=False):
        adapter = DjangoLoggingSettingsAdapter()

    assert adapter.debug is False


def test_logging_adapter_isolates_development_log_files_by_process():
    with override_settings(DEBUG=True, LOG_FILE_ENABLED=True, LOG_DIR="logs"):
        adapter = DjangoLoggingSettingsAdapter()

    assert Path(adapter.log_dir).name == f"process-{os.getpid()}"
