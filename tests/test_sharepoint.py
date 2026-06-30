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
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from justifactu.sharepoint import (
    #    _connect_sharepoint,
    get_list_id,
    get_site_id,
    get_drive_id,
    list_folder_contents,
)

# def test_sharepoint_connection():
#    """Test that sharepoint connection works."""
#    token_manager, site_id, drive_id = _connect_sharepoint()
#    assert site_id
#    assert drive_id


# ── helpers ───────────────────────────────────────────────────────────────────


def _mock_token_manager(token: str = "fake-token") -> MagicMock:
    tm = MagicMock()
    tm.get_token.return_value = token
    return tm


def _ok_response(json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


# ── get_list_id ───────────────────────────────────────────────────────────────


def test_get_list_id_returns_id_happy():
    tm = _mock_token_manager()
    resp = _ok_response({"id": "list-guid-123"})
    with patch("justifactu.sharepoint.requests.get", return_value=resp) as mock_get:
        list_id_result = get_list_id(tm, "site-id", "MyList")
    assert list_id_result == "list-guid-123"
    url = mock_get.call_args[0][0]
    assert "site-id" in url
    assert "MyList" in url


def test_get_list_id_raises_http_error():
    tm = _mock_token_manager()
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
    with patch("justifactu.sharepoint.requests.get", return_value=resp):
        with pytest.raises(requests.exceptions.HTTPError):
            get_list_id(tm, "site-id", "MissingList")


# ── get_site_id ───────────────────────────────────────────────────────────────


def test_get_site_id_returns_id_happy():
    tm = _mock_token_manager()
    resp = _ok_response({"id": "site-id"})
    with patch("justifactu.sharepoint.requests.get", return_value=resp) as mock_get:
        site_id_result = get_site_id(tm, "site-id", "MyList")
    assert site_id_result == "site-id"
    url = mock_get.call_args[0][0]
    assert "site-id" in url
    assert "MyList" in url


def test_get_site_id_raises_http_error():
    tm = _mock_token_manager()
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
    with patch("justifactu.sharepoint.requests.get", return_value=resp):
        with pytest.raises(requests.exceptions.HTTPError):
            get_site_id(tm, "site-id", "MissingList")


# ── get_drive_id ──────────────────────────────────────────────────────────────


def test_get_drive_id_returns_id_happy():
    tm = _mock_token_manager()
    resp = _ok_response({"value": [{"name": "Documents", "id": "drive-id"}]})
    with patch("justifactu.sharepoint.requests.get", return_value=resp) as mock_get:
        drive_id_result = get_drive_id(tm, "site-id")
    assert drive_id_result == "drive-id"
    url = mock_get.call_args[0][0]
    assert "site-id" in url


def test_get_drive_id_raises_http_error():
    tm = _mock_token_manager()
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
    with patch("justifactu.sharepoint.requests.get", return_value=resp):
        with pytest.raises(requests.exceptions.HTTPError):
            get_drive_id(tm, "site-id")


def test_get_drive_id_raises_exception_drive_not_found():
    tm = _mock_token_manager()
    resp = _ok_response({"value": [{"name": "OtherDrive", "id": "other-id"}]})
    with patch("justifactu.sharepoint.requests.get", return_value=resp):
        with pytest.raises(Exception, match="no encontrado"):
            get_drive_id(tm, "site-id")


# ── list_folder_contents ─────────────────────────────────────────────────────


def test_list_folder_contents_returns_items_happy():
    tm = _mock_token_manager()
    items = [
        {"name": "factura1.pdf", "id": "item1"},
        {"name": "factura2.pdf", "id": "item2"},
        {"name": "informe.xslx", "id": "item3"},
    ]
    resp = _ok_response({"value": items})
    with patch("justifactu.sharepoint.requests.get", return_value=resp) as mock_get:
        result = list_folder_contents(tm, "drive-id", Path("folder/subfolder"))
    assert result == items
    url = mock_get.call_args[0][0]
    assert "drive-id" in url
    assert "folder/subfolder" in url


def test_list_folder_contents_raises_http_error():
    tm = _mock_token_manager()
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
    with patch("justifactu.sharepoint.requests.get", return_value=resp):
        with pytest.raises(requests.exceptions.HTTPError):
            list_folder_contents(tm, "drive-id", Path("folder/subfolder"))
