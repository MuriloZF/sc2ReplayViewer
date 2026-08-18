from pathlib import Path

import pytest

from backend.app.cli import main


def test_cli_reports_missing_replay(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    exit_code = main([str(tmp_path / "missing.SC2Replay")])

    assert exit_code == 1
    assert "Replay file does not exist" in capsys.readouterr().err
