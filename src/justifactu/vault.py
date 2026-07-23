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

"""HashiCorp Vault client for fetching runtime secrets via AppRole authentication."""

import os
from typing import cast

import requests
import urllib3
from pathlib import Path

from .defines import SecretNames, ROOT_FOLDER
from .logger import get_logger
from .custom_except import VaultSecretEmpty

_VAULT_BASE_PATH = "secret/data/justifactu/runtime"

# Maps app-level secret names to (vault subpath, vault field key)
_SECRET_MAP = {
    # sharepoint
    SecretNames.CLIENT_ID.value: ("sharepoint", "client_id"),
    SecretNames.CLIENT_NAME.value: ("sharepoint", "client_name"),
    SecretNames.CLIENT_SECRET.value: ("sharepoint", "client_secret"),
    SecretNames.OBJECT_ID.value: ("sharepoint", "object_id"),
    SecretNames.SHAREPOINT_DOMAIN.value: ("sharepoint", "domain"),
    SecretNames.DRIVE_ID.value: ("sharepoint", "drive_id"),
    SecretNames.SHAREPOINT_LIST_GUID.value: ("sharepoint", "list_guid"),
    SecretNames.SHAREPOINT_LIST_NAME.value: ("sharepoint", "list_name"),
    SecretNames.SITE_NAME.value: ("sharepoint", "site_name"),
    SecretNames.TENANT_ID.value: ("sharepoint", "tenant_id"),
    # smtp
    SecretNames.SMTP_PASSWORD.value: ("smtp", "password"),
    SecretNames.SMTP_PORT.value: ("smtp", "port"),
    SecretNames.SMTP_SERVER.value: ("smtp", "host"),
    SecretNames.SMTP_USERNAME: ("smtp", "username"),
    SecretNames.SMTP_DEVELOPER_EMAIL.value: ("smtp", "developer_email"),
    SecretNames.SMTP_OWNER_EMAIL.value: ("smtp", "owner_email"),
    SecretNames.SMTP_ADMIN_EMAIL.value: ("smtp", "admin_email"),
}


log = get_logger(__name__)


def _read_credential(name: str) -> str:
    """Read a credential value, trying sources in priority order.

    Sources tried in order:
      1. ``/run/secrets/<name>``
      2. ``<project_root>/secrets/<name>``
      3. Environment variable named *name*

    Args:
        name: Credential name to look up.

    Returns:
        The credential value as a stripped string.

    Raises:
        KeyError: If the credential is not found in any source.
    """
    for path in (Path("/run/secrets") / name, ROOT_FOLDER / "secrets" / name):
        if path.is_file():
            with open(path) as f:
                value = f.read().strip()
            if value:
                return value
    value = os.environ.get(name, "").strip()
    log.debug(f"Read secret from {name}")
    if value:
        return value
    raise KeyError(f"Vault credential '{name}' not found in secrets or environment")


class _VaultClient:
    """Internal Vault client with token caching and AppRole authentication."""

    def __init__(self) -> None:
        """Initialise the client and configure TLS from available credentials."""
        self._token: str | None = None
        self._cache: dict[str, dict[str, str]] = {}  # subpath -> {field: value}

        self._session = requests.Session()
        ca_cert = _read_credential("VAULT_CACERT").strip()
        if ca_cert:
            ca_cert_path = Path(ca_cert)
            if not ca_cert_path.is_absolute():
                ca_cert_path = ROOT_FOLDER / ca_cert_path
            self._session.verify = str(ca_cert_path)
        elif _read_credential("VAULT_SKIP_VERIFY").lower() in ("1", "true", "yes"):
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self._session.verify = False
        # If neither is set, requests will use its default CA bundle.

    def _authenticate(self) -> None:
        """Authenticate against Vault using a token or AppRole credentials."""
        # 1. Try a pre-issued Vault token.
        try:
            self._token = _read_credential("VAULT_TOKEN")
            return
        except KeyError:
            pass

        # 2. Try AppRole (VAULT_ROLE_ID + VAULT_SECRET_ID).
        role_id = _read_credential("VAULT_ROLE_ID")
        secret_id = _read_credential("VAULT_SECRET_ID")
        vault_addr = _read_credential("VAULT_ADDR")
        resp = self._session.post(
            f"{vault_addr}/v1/auth/approle/login",
            json={"role_id": role_id, "secret_id": secret_id},
            timeout=10,
        )
        resp.raise_for_status()
        self._token = cast(str, resp.json()["auth"]["client_token"])

    def _fetch_subpath(self, subpath: str) -> dict[str, str]:
        """Fetch and cache all fields from a Vault KV sub-path.

        Args:
            subpath: The sub-path under ``_VAULT_BASE_PATH`` to fetch.

        Returns:
            Dictionary of field names to their string values.
        """
        if subpath in self._cache:
            return self._cache[subpath]

        if self._token is None:
            self._authenticate()
        if self._token is None:
            raise RuntimeError(
                "Vault authentication completed without producing a token"
            )
        vault_addr = _read_credential("VAULT_ADDR")
        url = f"{vault_addr}/v1/{_VAULT_BASE_PATH}/{subpath}"
        resp = self._session.get(
            url,
            headers={"X-Vault-Token": self._token},
            timeout=10,
        )
        resp.raise_for_status()
        data = cast(dict[str, str], resp.json()["data"]["data"])
        self._cache[subpath] = data
        return data

    def read_secret(self, secret_name: str) -> str:
        """Return the value of a named secret from Vault.

        Args:
            secret_name: Application-level secret name defined in ``_SECRET_MAP``.

        Returns:
            The secret value as a string.

        Raises:
            KeyError: If *secret_name* has no mapping or the field is absent.
            ValueError: If the field exists but is empty.
        """
        if secret_name not in _SECRET_MAP:
            raise KeyError(f"No vault mapping defined for secret '{secret_name}'")
        subpath, field = _SECRET_MAP[secret_name]
        data = self._fetch_subpath(subpath)
        if field not in data:
            raise KeyError(
                f"Field '{field}' not found at vault path '{_VAULT_BASE_PATH}/{subpath}'"
            )
        value = data[field]
        if value is None or str(value).strip() == "":
            raise VaultSecretEmpty(
                f"Vault secret '{secret_name}' (field '{field}') is empty"
            )
        return str(value)


_client = None


def read_vault_secret(secret_name: str) -> str:
    """Return the value of *secret_name* fetched from Vault.

    Raises KeyError  if the secret has no vault mapping or the field is absent.
    Raises ValueError if the field exists but is empty.
    Raises requests.HTTPError / ConnectionError on network / auth failures.
    """
    log.trace(f"requested secret from vault: {secret_name}")
    global _client
    if _client is None:
        _client = _VaultClient()
    return _client.read_secret(secret_name)
