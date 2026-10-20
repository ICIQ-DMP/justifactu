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

from justifactu.bank_statement import (
    BankEntry,
    _group_into_rows,
    _parse_amount,
    extract_bank_entries,
    Word,
)

sap_id = "2034567890"


# ── _parse_amount ─────────────────────────────────────────────────────────────


def test_parse_amount_simple():
    assert _parse_amount("56,78") == 56.78


def test_parse_amount_with_thousands_separator():
    assert _parse_amount("1.234,56") == 1234.56


# ── _group_into_rows ──────────────────────────────────────────────────────────


def test_group_into_rows_groups_same_top():

    word_a: Word = {"text": "0101", "x0": 10.0, "top": 100.0}
    word_b: Word = {"text": "Compra", "x0": 50.0, "top": 100.0}
    result = _group_into_rows([word_a, word_b])
    assert result == [[word_a, word_b]]


def test_group_into_rows_separates_different_top():

    word_a: Word = {"text": "0101", "x0": 10.0, "top": 100.0}
    word_b: Word = {"text": "Compra", "x0": 50.0, "top": 150.0}
    result = _group_into_rows([word_a, word_b])
    assert result == [[word_a], [word_b]]


def test_group_into_rows_sorts_row_left_to_right():
    word_a: Word = {"text": "0101", "x0": 10.0, "top": 100.0}
    word_b: Word = {"text": "Compra", "x0": 50.0, "top": 100.0}
    result = _group_into_rows([word_b, word_a])
    assert result == [[word_a, word_b]]


# ── extract_bank_entries ───────────────────────────────────────────────────────


def test_extract_bank_entries_parses_valid_row(tmp_path):
    pdf_path = tmp_path / "statement.pdf"
    pdf_path.touch()

    mock_page = MagicMock()
    mock_page.extract_words.return_value = [
        {"text": "0101", "x0": 0.0, "top": 100.0},
        {"text": "Compra", "x0": 70.0, "top": 100.0},
        {"text": "56,78", "x0": 300.0, "top": 100.0},
    ]
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdfplumber_open = MagicMock()
    mock_pdfplumber_open.__enter__.return_value = mock_pdf

    with patch(
        "justifactu.bank_statement.pdfplumber.open", return_value=mock_pdfplumber_open
    ):
        result = extract_bank_entries(pdf_path)

    assert result == [BankEntry(date="0101", concept="Compra", total=56.78)]


def test_extract_bank_entries_skips_non_transaction_rows(tmp_path):
    pdf_path = tmp_path / "statement.pdf"
    pdf_path.touch()

    mock_page = MagicMock()
    mock_page.extract_words.return_value = [
        {"text": "01001", "x0": 0.0, "top": 100.0},
        {"text": "Compra", "x0": 70.0, "top": 100.0},
        {"text": "56,78", "x0": 300.0, "top": 100.0},
    ]
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdfplumber_open = MagicMock()
    mock_pdfplumber_open.__enter__.return_value = mock_pdf

    with patch(
        "justifactu.bank_statement.pdfplumber.open", return_value=mock_pdfplumber_open
    ):
        result = extract_bank_entries(pdf_path)

    assert result == []


def test_extract_bank_entries_skips_row_with_no_amount(tmp_path):
    pdf_path = tmp_path / "statement.pdf"
    pdf_path.touch()

    mock_page = MagicMock()
    mock_page.extract_words.return_value = [
        {"text": "0101", "x0": 0.0, "top": 100.0},
        {"text": "Compra", "x0": 70.0, "top": 100.0},
    ]
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdfplumber_open = MagicMock()
    mock_pdfplumber_open.__enter__.return_value = mock_pdf

    with patch(
        "justifactu.bank_statement.pdfplumber.open", return_value=mock_pdfplumber_open
    ):
        result = extract_bank_entries(pdf_path)

    assert result == []


def test_extract_bank_entries_excludes_words_past_concept_column(tmp_path):
    pdf_path = tmp_path / "statement.pdf"
    pdf_path.touch()

    mock_page = MagicMock()
    mock_page.extract_words.return_value = [
        {"text": "0101", "x0": 0.0, "top": 100.0},
        {"text": "Compra", "x0": 70.0, "top": 100.0},
        {"text": "Patata", "x0": 290.0, "top": 100.0},
        {"text": "56,78", "x0": 300.0, "top": 100.0},
    ]
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdfplumber_open = MagicMock()
    mock_pdfplumber_open.__enter__.return_value = mock_pdf

    with patch(
        "justifactu.bank_statement.pdfplumber.open", return_value=mock_pdfplumber_open
    ):
        result = extract_bank_entries(pdf_path)

    assert result == [BankEntry(date="0101", concept="Compra", total=56.78)]


def test_extract_bank_entries_combines_multiple_pages(tmp_path):
    pdf_path = tmp_path / "statement.pdf"
    pdf_path.touch()
    mock_page_1 = MagicMock()
    mock_page_2 = MagicMock()
    mock_page_1.extract_words.return_value = [
        {"text": "0101", "x0": 0.0, "top": 100.0},
        {"text": "Compra", "x0": 70.0, "top": 100.0},
        {"text": "56,78", "x0": 300.0, "top": 100.0},
    ]
    mock_page_2.extract_words.return_value = [
        {"text": "0202", "x0": 0.0, "top": 100.0},
        {"text": "Taxi", "x0": 70.0, "top": 100.0},
        {"text": "82,99", "x0": 300.0, "top": 100.0},
    ]
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page_1, mock_page_2]
    mock_pdfplumber_open = MagicMock()
    mock_pdfplumber_open.__enter__.return_value = mock_pdf
    with patch(
        "justifactu.bank_statement.pdfplumber.open", return_value=mock_pdfplumber_open
    ):
        result = extract_bank_entries(pdf_path)
    assert result == [
        BankEntry(date="0101", concept="Compra", total=56.78),
        BankEntry(date="0202", concept="Taxi", total=82.99),
    ]
