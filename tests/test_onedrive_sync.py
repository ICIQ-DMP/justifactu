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
from justifactu.onedrive_sync import run_onedrive_sync


def _confdir(tmp_path: Path) -> Path:
    confdir = tmp_path / "conf"
    confdir.mkdir()
    return confdir


def test_run_onedrive_sync_succeeds_without_resync(tmp_path):
    confdir = _confdir(tmp_path)

    with (
        patch("justifactu.onedrive_sync.read_secret", return_value="drive-id"),
        patch("justifactu.onedrive_sync.subprocess.run") as mock_run,
    ):
        run_onedrive_sync(
            confdir,
            direction="download",
            single_dir=Path("justifactu/runtime"),
            data_folder=tmp_path / "data",
        )

    mock_run.assert_called_once()
    assert "--resync" not in mock_run.call_args[0][0]


def test_run_onedrive_sync_retries_once_with_resync_on_126(tmp_path):
    confdir = _confdir(tmp_path)

    with (
        patch("justifactu.onedrive_sync.read_secret", return_value="drive-id"),
        patch(
            "justifactu.onedrive_sync.subprocess.run",
            side_effect=[
                subprocess.CalledProcessError(126, "onedrive"),
                None,
            ],
        ) as mock_run,
    ):
        run_onedrive_sync(
            confdir,
            direction="download",
            single_dir=Path("justifactu/runtime"),
            data_folder=tmp_path / "data",
        )

    assert mock_run.call_count == 2
    retry_args = mock_run.call_args_list[1][0][0]
    assert "--resync" in retry_args
    assert "--resync-auth" in retry_args


def test_run_onedrive_sync_does_not_retry_on_other_failures(tmp_path):
    confdir = _confdir(tmp_path)

    with (
        patch("justifactu.onedrive_sync.read_secret", return_value="drive-id"),
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
        )

    mock_run.assert_called_once()
