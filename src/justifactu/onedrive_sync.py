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

from .custom_except import MainCriticalError
from .logger import get_logger

log = get_logger(__name__)


def run_onedrive_sync(confdir: Path, direction: str, syncdir: Path) -> None:
    """Runs a one-shot OneDrive-for-Linux sync and blocks until it exits.

    Args:
        confdir: Path to the onedrive client's config directory.
        direction: "download" or "upload" — becomes --download-only / --upload-only.
        syncdir: Path to the onedrive sync's directory.
    Raises:
        MainCriticalError: If the onedrive process exits non-zero, or the
            binary isn't installed.
    """

    log.info(f"Starting onedrive {direction} sync...")
    try:
        subprocess.run(
            [
                "onedrive",
                "--confdir",
                str(confdir),
                "--sync",
                "--single-directory",
                str(syncdir),
                f"--{direction}-only",
                "--verbose",
            ],
            check=True,
        )
        log.info(f"OneDrive {direction} sync complete.")
    except subprocess.CalledProcessError as e:
        raise MainCriticalError(
            f"OneDrive {direction} sync failed with code {e.returncode}."
        ) from e
    except FileNotFoundError as e:
        raise MainCriticalError("onedrive binary not found on PATH") from e
