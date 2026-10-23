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
from .defines import Mode, SecretNames
from .secret import read_secret

log = get_logger(__name__)


def _drive_id_present(confdir: Path) -> bool:
    """Whether the config file already has a non-empty drive_id value."""
    config_path = confdir / "config"
    if not config_path.exists():
        return False
    for line in config_path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("drive_id"):
            _, _, value = stripped.partition("=")
            return value.strip().strip('"') != ""
    return False


def _write_drive_id_if_missing(confdir: Path) -> None:
    """Writes the drive_id secret into the onedrive config file, but only
    the first time — if a non-empty drive_id is already there, this is a
    no-op. Unlike the old write-then-erase-every-call approach, the value
    now persists once written, so the config file's content stays stable
    across runs instead of churning on every invocation — churn that used
    to make onedrive's own .config.backup change-detection think the
    config had been edited and demand a --resync."""
    if _drive_id_present(confdir):
        return

    config_path = confdir / "config"
    config_path.touch(exist_ok=True)
    lines = config_path.read_text().splitlines()
    drive_id = read_secret(SecretNames.DRIVE_ID.value)
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


# onedrive's own app-specific exit code for "the config differs from the last run's
# .config.backup (or no backup exists yet) and a --resync is required before it will sync".
# Hit on the first real sync after a fresh --auth bootstrap, since run_onedrive_auth never
# invokes the sync engine and so never writes that backup.
_RESYNC_REQUIRED_EXIT_CODE = 126


def _base_onedrive_args(confdir: Path, data_folder: Path, mode: Mode) -> list[str]:
    """Flags shared by every sync invocation (download/upload)."""
    args_list = [
        "onedrive",
        "--confdir",
        str(confdir),
        "--syncdir",
        str(data_folder),
    ]
    if mode != Mode.PROD:
        # Passed twice: a single --verbose only enables onedrive's own verboseLogging;
        # the per-field debug lines around its config-change/--resync detection (which
        # field it thinks changed, or whether .config.backup/.config.hash exist at
        # check time) are gated behind debugLogging, which needs --verbose repeated.
        # Left out in PROD so logs don't grow unbounded on real runs.
        args_list += ["--verbose", "--verbose"]
    return args_list


def run_onedrive_sync(
    confdir: Path,
    direction: str,
    single_dir: Path,
    data_folder: Path,
    mode: Mode,
    dry_run: bool = False,
) -> None:
    """Runs a one-shot OneDrive-for-Linux sync and blocks until it exits."""
    log.info(f"Starting onedrive {direction} sync...")
    try:
        _write_drive_id_if_missing(confdir)

        args_list = _base_onedrive_args(confdir, data_folder, mode)
        args_list += [
            "--sync",
            f"--{direction}-only",
            "--single-directory",
            str(single_dir),
        ]
        if direction == "download":
            args_list.append("--cleanup-local-files")
        # No equivalent flag needed for "upload": onedrive already deletes remote
        # files that no longer exist locally on --upload-only by default (its
        # no_remote_delete setting defaults to false) — --no-remote-delete is the
        # opt-OUT flag, so simply not passing it keeps that cleanup behavior on.
        if dry_run:
            args_list.append("--dry-run")

        try:
            subprocess.run(args_list, check=True)
        except subprocess.CalledProcessError as e:
            if e.returncode != _RESYNC_REQUIRED_EXIT_CODE:
                raise
            log.warning(
                "OneDrive requires a --resync (no matching .config.backup found); "
                "retrying once with --resync --resync-auth."
            )
            subprocess.run(args_list + ["--resync", "--resync-auth"], check=True)
        log.info(f"OneDrive {direction} sync complete.")
    except subprocess.CalledProcessError as e:
        raise MainCriticalError(
            f"OneDrive {direction} sync failed with code {e.returncode}."
        ) from e
    except FileNotFoundError as e:
        raise MainCriticalError("onedrive binary not found on PATH") from e


def run_onedrive_auth(confdir: Path, data_folder: Path, mode: Mode) -> None:
    """Runs a one-shot OneDrive-for-Linux authentication pass.

    No --single-directory, no --sync/--monitor: on a confdir with no
    existing refresh token this drives the interactive OAuth flow,
    persists the token, and exits — no file listing or transfer happens.
    """
    log.info("Starting onedrive authentication...")
    try:
        _write_drive_id_if_missing(confdir)

        args_list = _base_onedrive_args(confdir, data_folder, mode)

        subprocess.run(args_list, check=True)
        log.info("OneDrive authentication complete.")
    except subprocess.CalledProcessError as e:
        raise MainCriticalError(
            f"OneDrive authentication failed with code {e.returncode}."
        ) from e
    except FileNotFoundError as e:
        raise MainCriticalError("onedrive binary not found on PATH") from e
