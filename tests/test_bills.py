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

from unittest.mock import MagicMock, patch

import pytest

from justifactu.pdf import parse_sap_id_from_bill
from justifactu.custom_except import ParseSAPIdException

SAP_ID = "2034567890"


# ── parse_sap_id_from_bill ────────────────────────────────────────────────────


def test_parse_sap_id_from_bill_found(tmp_path):
    pdf_path = tmp_path / "bill.pdf"
    pdf_path.touch()

    mock_page = MagicMock()
    mock_page.extract_text.return_value = f"Fra. {SAP_ID} some other text"
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch("justifactu.pdf.PdfReader", return_value=mock_reader):
        result = parse_sap_id_from_bill(pdf_path)

    assert result == SAP_ID


def test_parse_sap_id_from_bill_found_without_dot(tmp_path):
    pdf_path = tmp_path / "bill.pdf"
    pdf_path.touch()

    mock_page = MagicMock()
    mock_page.extract_text.return_value = f"Fra {SAP_ID}"
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch("justifactu.pdf.PdfReader", return_value=mock_reader):
        result = parse_sap_id_from_bill(pdf_path)

    assert result == SAP_ID


def test_parse_sap_id_from_bill_not_found_raises(tmp_path):
    pdf_path = tmp_path / "bill.pdf"
    pdf_path.touch()

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Some unrelated text"
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch("justifactu.pdf.PdfReader", return_value=mock_reader):
        with pytest.raises(ParseSAPIdException, match="No SAP ID found"):
            parse_sap_id_from_bill(pdf_path)


def test_parse_sap_id_from_bill_skips_empty_pages(tmp_path):
    pdf_path = tmp_path / "bill.pdf"
    pdf_path.touch()

    empty_page = MagicMock()
    empty_page.extract_text.return_value = None
    good_page = MagicMock()
    good_page.extract_text.return_value = f"Fra. {SAP_ID}"
    mock_reader = MagicMock()
    mock_reader.pages = [empty_page, good_page]

    with patch("justifactu.pdf.PdfReader", return_value=mock_reader):
        result = parse_sap_id_from_bill(pdf_path)

    assert result == SAP_ID
