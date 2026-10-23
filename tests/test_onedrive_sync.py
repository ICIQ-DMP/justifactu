# justifactu - Automated billing justifications
# Copyright (C) 2026  Aleix Mariné Tena (AleixMT), Carles de la Cuadra, David Romero San Millán (DavidRomeroICIQ)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from justifactu.custom_except import MainCriticalError
from justifactu.defines import Mode
from justifactu.onedrive_sync import (
    _base_onedrive_args,
    _drive_id_present,
    _write_drive_id_if_missing,
    run_onedrive_sync,
)


def _confdir(tmp_path: Path) -> Path:
    confdir = tmp_path / "conf"
    confdir.mkdir()
    return confdir


# ── _drive_id_present ───────────────────────────────────────────────────────


def test_drive_id_present_false_when_config_missing(tmp_path):
    confdir = _confdir(tmp_path)
    assert _drive_id_present(confdir) is False


def test_drive_id_present_false_when_blank(tmp_path):
    confdir = _confdir(tmp_path)
    (confdir / "config").write_text('drive_id = ""\n')
    assert _drive_id_present(confdir) is False


def test_drive_id_present_true_when_set(tmp_path):
    confdir = _confdir(tmp_path)
    (confdir / "config").write_text('drive_id = "abc123"\n')
    assert _drive_id_present(confdir) is True


# ── _write_drive_id_if_missing ──────────────────────────────────────────────


def test_write_drive_id_if_missing_writes_when_absent(tmp_path):
    confdir = _confdir(tmp_path)

    with patch(
        "justifactu.onedrive_sync.read_secret", return_value="real-drive-id"
    ) as mock_secret:
        _write_drive_id_if_missing(confdir)

    mock_secret.assert_called_once()
    assert 'drive_id = "real-drive-id"' in (confdir / "config").read_text()


def test_write_drive_id_if_missing_is_noop_when_present(tmp_path):
    confdir = _confdir(tmp_path)
    (confdir / "config").write_text('drive_id = "already-there"\n')

    with patch("justifactu.onedrive_sync.read_secret") as mock_secret:
        _write_drive_id_if_missing(confdir)

    mock_secret.assert_not_called()
    assert (confdir / "config").read_text() == 'drive_id = "already-there"\n'


# ── _base_onedrive_args ──────────────────────────────────────────────────────


@pytest.mark.parametrize("mode", [Mode.TEST, Mode.DEV])
def test_base_onedrive_args_includes_double_verbose_outside_prod(tmp_path, mode):
    args_list = _base_onedrive_args(tmp_path / "conf", tmp_path / "data", mode)
    assert args_list.count("--verbose") == 2


def test_base_onedrive_args_excludes_verbose_in_prod(tmp_path):
    args_list = _base_onedrive_args(tmp_path / "conf", tmp_path / "data", Mode.PROD)
    assert "--verbose" not in args_list


# ── run_onedrive_sync ────────────────────────────────────────────────────────


def test_run_onedrive_sync_succeeds_without_resync(tmp_path):
    confdir = _confdir(tmp_path)
    (confdir / "config").write_text('drive_id = "already-there"\n')

    with patch("justifactu.onedrive_sync.subprocess.run") as mock_run:
        run_onedrive_sync(
            confdir,
            direction="download",
            single_dir=Path("justifactu/runtime"),
            data_folder=tmp_path / "data",
            mode=Mode.TEST,
        )

    mock_run.assert_called_once()
    assert "--resync" not in mock_run.call_args[0][0]


def test_run_onedrive_sync_retries_once_with_resync_on_126(tmp_path):
    confdir = _confdir(tmp_path)
    (confdir / "config").write_text('drive_id = "already-there"\n')

    with patch(
        "justifactu.onedrive_sync.subprocess.run",
        side_effect=[
            subprocess.CalledProcessError(126, "onedrive"),
            None,
        ],
    ) as mock_run:
        run_onedrive_sync(
            confdir,
            direction="download",
            single_dir=Path("justifactu/runtime"),
            data_folder=tmp_path / "data",
            mode=Mode.TEST,
        )

    assert mock_run.call_count == 2
    retry_args = mock_run.call_args_list[1][0][0]
    assert "--resync" in retry_args
    assert "--resync-auth" in retry_args


def test_run_onedrive_sync_does_not_retry_on_other_failures(tmp_path):
    confdir = _confdir(tmp_path)
    (confdir / "config").write_text('drive_id = "already-there"\n')

    with (
        patch(
            "justifactu.onedrive_sync.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "onedrive"),
        ) as mock_run,
        pytest.raises(MainCriticalError),
    ):
        run_onedrive_sync(
            confdir,
            direction="download",
            single_dir=Path("justifactu/runtime"),
            data_folder=tmp_path / "data",
            mode=Mode.TEST,
        )

    mock_run.assert_called_once()
