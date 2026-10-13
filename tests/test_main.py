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


from justifactu.defines import InputLocation


def _auth_args(tmp_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        auth=True,
        location=InputLocation.SHAREPOINT,
        onedrive_conf_folder=tmp_path / "conf",
        onedrive_data_folder=tmp_path / "data",
        dry_run=False,
    )
