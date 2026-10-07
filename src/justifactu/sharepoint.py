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

"""Microsoft Graph API download path — fallback for when the OneDrive-for-Linux
sync fails. Not the primary input path; see onedrive_sync.py for that."""

import time
from pathlib import Path
from typing import cast

import requests
from requests.exceptions import HTTPError

from .defines import SecretNames
from .logger import get_logger
from .secret import read_secret
from .token_manager import TokenManager, get_token_manager

log = get_logger(__name__)


def get_site_id(token_manager: TokenManager, domain: str, site_name: str) -> str:
    """Return the compound site identifier for a SharePoint site."""
    url = f"https://graph.microsoft.com/v1.0/sites/{domain}:/sites/{site_name}"
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    the_id = cast(str, response.json()["id"])
    return the_id


def get_drive_id(
    token_manager: TokenManager, site_id: str, drive_name: str = "Documents"
) -> str:
    """Return the drive ID of the named document library."""
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    drives = response.json()["value"]
    for drive in drives:
        if drive["name"] == drive_name:
            return cast(str, drive["id"])
    raise Exception(f"Drive '{drive_name}' not found.")


def list_folder_contents(
    token_manager: TokenManager, drive_id: str, path: Path
) -> list[dict[str, str]]:
    """Return the children items of a remote drive folder."""
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{path}:/children"
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return cast(list[dict[str, str]], response.json()["value"])


def download_file(
    token_manager: TokenManager,
    drive_id: str,
    item_path: Path,
    local_path: Path,
    max_retries: int = 5,
) -> None:
    """Download a single file from the drive, retrying on HTTP 503."""
    url = (
        f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{item_path}:/content"
    )
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}

    retry_count = 0
    backoff = 2

    while retry_count <= max_retries:
        response = None
        try:
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()

            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            log.trace(f"Downloaded: {item_path}")
            return

        except HTTPError as e:
            if response is None:
                raise e
            if response.status_code == 503:
                retry_count += 1
                wait_time = backoff * retry_count
                log.warning(
                    f"Error 503 in '{item_path}' - retrying in {wait_time}s (attempt {retry_count}/{max_retries})..."
                )
                time.sleep(wait_time)
            else:
                raise e

    raise RuntimeError(
        f"Permanent fail when downloading '{item_path}' after {max_retries} attempts."
    )


def download_folder_recursive(
    token_manager: TokenManager, drive_id: str, remote_path: Path, local_root: Path
) -> None:
    """Recursively download all files under remote_path to local_root."""
    items = list_folder_contents(token_manager, drive_id, remote_path)
    for item in items:
        name = Path(item["name"])
        item_path = remote_path / name
        local_path = local_root / name

        if "folder" in item:
            download_folder_recursive(token_manager, drive_id, item_path, local_path)
        elif "file" in item:
            download_file(token_manager, drive_id, item_path, local_path)


def download_input_folder(
    token_manager: TokenManager, drive_id: str, remote_path: Path, input_path: Path
) -> None:
    """Download the entire input folder from SharePoint to a local path."""
    log.info("Starting recursive download from SharePoint via Graph API...")
    download_folder_recursive(token_manager, drive_id, remote_path, input_path)
    log.info("Graph API download completed.")


def connect_sharepoint() -> tuple[TokenManager, str, str]:
    """Authenticate with SharePoint and return (token_manager, site_id, drive_id)."""
    token_manager = get_token_manager()
    sharepoint_domain = read_secret(SecretNames.SHAREPOINT_DOMAIN.value)
    site_name = read_secret(SecretNames.SITE_NAME.value)
    site_id = get_site_id(token_manager, sharepoint_domain, site_name)
    drive_id = get_drive_id(token_manager, site_id, drive_name="Documents")
    return token_manager, site_id, drive_id
