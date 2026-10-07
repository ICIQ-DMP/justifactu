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
from .defines import SecretNames
from .secret import read_secret

log = get_logger(__name__)


def _set_drive_id(confdir: Path, drive_id: str) -> None:
    """Rewrites the drive_id line in the onedrive config file."""
    config_path = confdir / "config"
    lines = config_path.read_text().splitlines()
    new_lines = []
    found = False
    for line in lines:
        if line.strip().startswith("drive_id"):
            new_lines.append(f'drive_id = "{drive_id}"')
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f'drive_id = "{drive_id}"')
    config_path.write_text("\n".join(new_lines) + "\n")


def _write_drive_id(confdir: Path) -> None:
    """Writes the drive_id secret into the onedrive config file at launch,
    so the real value is never permanently stored in the git-tracked file."""
    _set_drive_id(confdir, read_secret(SecretNames.DRIVE_ID.value))


def erase_drive_id(confdir: Path) -> None:
    """Blanks the drive_id line in the onedrive config file, so the real
    value does not sit on disk between runs."""
    _set_drive_id(confdir, "")


def _base_onedrive_args(confdir: Path, data_folder: Path) -> list[str]:
    """Flags shared by every sync invocation (download/upload)."""
    return [
        "onedrive",
        "--confdir",
        str(confdir),
        "--syncdir",
        str(data_folder),
        "--verbose",
    ]


def run_onedrive_sync(
    confdir: Path,
    direction: str,
    single_dir: Path,
    data_folder: Path,
    dry_run: bool = False,
) -> None:
    """Runs a one-shot OneDrive-for-Linux sync and blocks until it exits."""
    log.info(f"Starting onedrive {direction} sync...")
    try:
        _write_drive_id(confdir)

        args_list = _base_onedrive_args(confdir, data_folder)
        args_list += [
            "--sync",
            f"--{direction}-only",
            "--single-directory",
            str(single_dir),
        ]
        if direction == "download":
            args_list.append("--cleanup-local-files")
        if dry_run:
            args_list.append("--dry-run")

        subprocess.run(args_list, check=True)
        log.info(f"OneDrive {direction} sync complete.")
    except subprocess.CalledProcessError as e:
        raise MainCriticalError(
            f"OneDrive {direction} sync failed with code {e.returncode}."
        ) from e
    except FileNotFoundError as e:
        raise MainCriticalError("onedrive binary not found on PATH") from e
    finally:
        try:
            erase_drive_id(confdir)
        except Exception as e:
            log.error(f"Failed to erase drive_id from onedrive config: {e}")


def run_onedrive_auth(confdir: Path, data_folder: Path) -> None:
    """Runs a one-shot OneDrive-for-Linux authentication pass.

    No --single-directory, no --sync/--monitor: on a confdir with no
    existing refresh token this drives the interactive OAuth flow,
    persists the token, and exits — no file listing or transfer happens.
    """
    log.info("Starting onedrive authentication...")
    try:
        _write_drive_id(confdir)

        args_list = _base_onedrive_args(confdir, data_folder)

        subprocess.run(args_list, check=True)
        log.info("OneDrive authentication complete.")
    except subprocess.CalledProcessError as e:
        raise MainCriticalError(
            f"OneDrive authentication failed with code {e.returncode}."
        ) from e
    except FileNotFoundError as e:
        raise MainCriticalError("onedrive binary not found on PATH") from e
    finally:
        try:
            erase_drive_id(confdir)
        except Exception as e:
            log.error(f"Failed to erase drive_id from onedrive config: {e}")
