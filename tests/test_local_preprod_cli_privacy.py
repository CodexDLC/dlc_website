"""CLI переноса не раскрывает детали ошибок подключения и записей."""

from unittest.mock import patch

import pytest

from scripts.local_preprod.cli import main


@pytest.mark.parametrize("phase", ["connection", "verification"])
def test_cli_masks_exception_details(tmp_path, monkeypatch, capsys, phase):
    source = tmp_path / "backup.sqlite3"
    source.touch()
    monkeypatch.setattr("sys.argv", ["transfer", "--source-sqlite", str(source), "--verify-only"])
    sensitive = "private-password-and-record-detail"
    with patch("scripts.local_preprod.cli.PostgresAdapter") as adapter, patch(
        "scripts.local_preprod.cli.PreprodTransferOrchestrator"
    ) as orchestrator:
        if phase == "connection":
            adapter.side_effect = RuntimeError(sensitive)
        else:
            orchestrator.return_value.verify.side_effect = RuntimeError(sensitive)
        assert main() == 1
    output = capsys.readouterr()
    assert sensitive not in output.err + output.out
    assert "RuntimeError" in output.err
