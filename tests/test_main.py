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
import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from justifactu.defines import InputLocation
from justifactu.main import main


def _auth_args(tmp_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        auth=True,
        location=InputLocation.SHAREPOINT,
        onedrive_conf_folder=tmp_path / "conf",
        onedrive_data_folder=tmp_path / "data",
        dry_run=False,
    )


def test_auth_branch_calls_run_onedrive_auth_and_exits_before_phases(tmp_path):
    args = _auth_args(tmp_path)

    with (
        patch("justifactu.main.process_parse_arguments", return_value=args),
        patch("justifactu.main.configure_logging_from_settings"),
        patch("justifactu.main.run_onedrive_auth") as mock_auth,
        patch("justifactu.main.run_onedrive_sync") as mock_sync,
        patch("justifactu.main.run_all_phases") as mock_phases,
        patch("builtins.exit", side_effect=SystemExit(0)) as mock_exit,
    ):
        with pytest.raises(SystemExit):
            main()

    mock_auth.assert_called_once_with(
        args.onedrive_conf_folder, data_folder=args.onedrive_data_folder
    )
    mock_exit.assert_called_once_with(0)
    mock_sync.assert_not_called()
    mock_phases.assert_not_called()
