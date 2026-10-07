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
from unittest.mock import MagicMock, call, patch

import pytest
import requests

from justifactu.sharepoint import (
    connect_sharepoint,
    download_file,
    download_folder_recursive,
    download_input_folder,
    get_drive_id,
    get_site_id,
    list_folder_contents,
)

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


def _streaming_response(chunks: list[bytes], status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.iter_content.return_value = chunks
    if status_code == 200:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resp)
    return resp


# ── get_site_id ───────────────────────────────────────────────────────────────


def test_get_site_id_returns_id_happy():
    tm = _mock_token_manager()
    resp = _ok_response({"id": "site-id"})
    with patch("justifactu.sharepoint.requests.get", return_value=resp) as mock_get:
        site_id_result = get_site_id(tm, "contoso.sharepoint.com", "MyList")
    assert site_id_result == "site-id"
    url = mock_get.call_args[0][0]
    assert "contoso.sharepoint.com" in url
    assert "MyList" in url


def test_get_site_id_raises_http_error():
    tm = _mock_token_manager()
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
    with patch("justifactu.sharepoint.requests.get", return_value=resp):
        with pytest.raises(requests.exceptions.HTTPError):
            get_site_id(tm, "contoso.sharepoint.com", "MissingList")


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
        with pytest.raises(Exception, match="not found"):
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


# ── download_file ─────────────────────────────────────────────────────────────


def test_download_file_writes_content_happy(tmp_path: Path):
    tm = _mock_token_manager()
    resp = _streaming_response([b"chunk1-", b"chunk2"])
    local_path = tmp_path / "nested" / "factura.pdf"
    with patch("justifactu.sharepoint.requests.get", return_value=resp) as mock_get:
        download_file(tm, "drive-id", Path("FACTURES/factura.pdf"), local_path)
    assert local_path.read_bytes() == b"chunk1-chunk2"
    url = mock_get.call_args[0][0]
    assert "drive-id" in url
    assert "FACTURES/factura.pdf" in url


def test_download_file_skips_empty_chunks(tmp_path: Path):
    tm = _mock_token_manager()
    resp = _streaming_response([b"data", b"", None])
    local_path = tmp_path / "factura.pdf"
    with patch("justifactu.sharepoint.requests.get", return_value=resp):
        download_file(tm, "drive-id", Path("factura.pdf"), local_path)
    assert local_path.read_bytes() == b"data"


def test_download_file_retries_on_503_then_succeeds(tmp_path: Path):
    tm = _mock_token_manager()
    fail_resp = _streaming_response([], status_code=503)
    ok_resp = _streaming_response([b"ok"])
    local_path = tmp_path / "factura.pdf"
    with (
        patch(
            "justifactu.sharepoint.requests.get",
            side_effect=[fail_resp, fail_resp, ok_resp],
        ) as mock_get,
        patch("justifactu.sharepoint.time.sleep") as mock_sleep,
    ):
        download_file(tm, "drive-id", Path("factura.pdf"), local_path, max_retries=5)
    assert local_path.read_bytes() == b"ok"
    assert mock_get.call_count == 3
    assert mock_sleep.call_count == 2


def test_download_file_raises_runtime_error_after_max_retries(tmp_path: Path):
    tm = _mock_token_manager()
    fail_resp = _streaming_response([], status_code=503)
    local_path = tmp_path / "factura.pdf"
    with (
        patch("justifactu.sharepoint.requests.get", return_value=fail_resp),
        patch("justifactu.sharepoint.time.sleep"),
    ):
        with pytest.raises(RuntimeError, match="Permanent fail"):
            download_file(
                tm, "drive-id", Path("factura.pdf"), local_path, max_retries=2
            )
    assert not local_path.exists()


def test_download_file_reraises_non_503_http_error_immediately(tmp_path: Path):
    tm = _mock_token_manager()
    fail_resp = _streaming_response([], status_code=404)
    local_path = tmp_path / "factura.pdf"
    with (
        patch("justifactu.sharepoint.requests.get", return_value=fail_resp) as mock_get,
        patch("justifactu.sharepoint.time.sleep") as mock_sleep,
    ):
        with pytest.raises(requests.exceptions.HTTPError):
            download_file(tm, "drive-id", Path("factura.pdf"), local_path)
    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()


# ── download_folder_recursive ─────────────────────────────────────────────────


def test_download_folder_recursive_downloads_files_and_recurses_into_subfolders():
    tm = _mock_token_manager()
    top_items = [
        {"name": "factura1.pdf", "file": {}},
        {"name": "subfolder", "folder": {}},
    ]
    sub_items = [{"name": "factura2.pdf", "file": {}}]

    with (
        patch(
            "justifactu.sharepoint.list_folder_contents",
            side_effect=[top_items, sub_items],
        ) as mock_list,
        patch("justifactu.sharepoint.download_file") as mock_download,
    ):
        download_folder_recursive(
            tm, "drive-id", Path("FACTURES"), Path("/local/FACTURES")
        )

    mock_list.assert_has_calls(
        [
            call(tm, "drive-id", Path("FACTURES")),
            call(tm, "drive-id", Path("FACTURES/subfolder")),
        ]
    )
    mock_download.assert_has_calls(
        [
            call(
                tm,
                "drive-id",
                Path("FACTURES/factura1.pdf"),
                Path("/local/FACTURES/factura1.pdf"),
            ),
            call(
                tm,
                "drive-id",
                Path("FACTURES/subfolder/factura2.pdf"),
                Path("/local/FACTURES/subfolder/factura2.pdf"),
            ),
        ]
    )


def test_download_folder_recursive_handles_empty_folder():
    tm = _mock_token_manager()
    with (
        patch("justifactu.sharepoint.list_folder_contents", return_value=[]),
        patch("justifactu.sharepoint.download_file") as mock_download,
    ):
        download_folder_recursive(tm, "drive-id", Path("Empty"), Path("/local/Empty"))
    mock_download.assert_not_called()


# ── download_input_folder ─────────────────────────────────────────────────────


def test_download_input_folder_delegates_to_recursive_download():
    tm = _mock_token_manager()
    with patch("justifactu.sharepoint.download_folder_recursive") as mock_recursive:
        download_input_folder(
            tm, "drive-id", Path("justifactu/runtime"), Path("/local/runtime")
        )
    mock_recursive.assert_called_once_with(
        tm, "drive-id", Path("justifactu/runtime"), Path("/local/runtime")
    )


# ── connect_sharepoint ─────────────────────────────────────────────────────────


def test_connect_sharepoint_returns_token_manager_site_id_and_drive_id():
    tm = _mock_token_manager()
    with (
        patch(
            "justifactu.sharepoint.get_token_manager", return_value=tm
        ) as mock_get_tm,
        patch(
            "justifactu.sharepoint.read_secret",
            side_effect=["contoso.sharepoint.com", "MySite"],
        ) as mock_read_secret,
        patch(
            "justifactu.sharepoint.get_site_id", return_value="site-id"
        ) as mock_site_id,
        patch(
            "justifactu.sharepoint.get_drive_id", return_value="drive-id"
        ) as mock_drive_id,
    ):
        result_tm, site_id, drive_id = connect_sharepoint()

    assert result_tm is tm
    assert site_id == "site-id"
    assert drive_id == "drive-id"
    mock_get_tm.assert_called_once()
    assert mock_read_secret.call_count == 2
    mock_site_id.assert_called_once_with(tm, "contoso.sharepoint.com", "MySite")
    mock_drive_id.assert_called_once_with(tm, "site-id", drive_name="Documents")
