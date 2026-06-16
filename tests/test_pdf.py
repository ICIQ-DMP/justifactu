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

# TODO: move functions regarding file movement into filesystem.py or others and do the corresponding for test functions
from unittest.mock import MagicMock, patch

import pytest

from conftest import create_blank_pdf
from justifactu.pdf import (
    change_file_name,
    cleanup_processed_files,
    copy_file,
    extract_sap_number,
    index_payments,
    merge_bills_and_payments,
    merge_pdfs,
    move_file,
    parse_sap_id_from_bill,
    rename_payments,
)

SAP_ID = "1234567890"


# ── copy_file ─────────────────────────────────────────────────────────────────


def test_copy_file_to_new_path(tmp_path):
    src = tmp_path / "src.pdf"
    src.touch()
    dst = tmp_path / "dst.pdf"

    copy_file(src, dst)

    assert dst.exists()
    assert src.exists()  # original is preserved


def test_copy_file_into_directory(tmp_path):
    src = tmp_path / "src.pdf"
    src.touch()
    dest_dir = tmp_path / "subdir"
    dest_dir.mkdir()

    copy_file(src, dest_dir)

    assert (dest_dir / "src.pdf").exists()


def test_copy_file_destination_exists_raises(tmp_path):
    src = tmp_path / "src.pdf"
    src.touch()
    dst = tmp_path / "dst.pdf"
    dst.touch()

    with pytest.raises(FileExistsError):
        copy_file(src, dst)


def test_copy_file_creates_parent_directories(tmp_path):
    src = tmp_path / "src.pdf"
    src.touch()
    dst = tmp_path / "a" / "b" / "dst.pdf"

    copy_file(src, dst)

    assert dst.exists()


# ── move_file ─────────────────────────────────────────────────────────────────


def test_move_file_success(tmp_path):
    src = tmp_path / "src.pdf"
    src.touch()
    dest_dir = tmp_path / "subdir"

    move_file(src, dest_dir)

    assert (dest_dir / "src.pdf").exists()
    assert not src.exists()


def test_move_file_creates_destination_directory(tmp_path):
    src = tmp_path / "src.pdf"
    src.touch()
    dest_dir = tmp_path / "new" / "nested"

    move_file(src, dest_dir)

    assert (dest_dir / "src.pdf").exists()


# ── change_file_name ──────────────────────────────────────────────────────────


def test_change_file_name_success(tmp_path):
    original = tmp_path / "old_name.pdf"
    original.touch()

    result = change_file_name(original, "new_name")

    assert result == tmp_path / "new_name.pdf"
    assert result.exists()
    assert not original.exists()


def test_change_file_name_nonexistent_returns_none(tmp_path):
    missing = tmp_path / "missing.pdf"
    result = change_file_name(missing, "anything")
    assert result is None


def test_change_file_name_collision_returns_none(tmp_path):
    original = tmp_path / "original.pdf"
    original.touch()
    conflict = tmp_path / "conflict.pdf"
    conflict.touch()

    result = change_file_name(original, "conflict")
    assert result is None


# ── extract_sap_number ────────────────────────────────────────────────────────


# TODO: create SAP class specialized in reading these numbers
def test_extract_sap_number_from_payment_filename():
    assert extract_sap_number("1234567890-P") == "1234567890"


def test_extract_sap_number_from_bill_filename():
    assert extract_sap_number("F 1234567890") == "1234567890"


def test_extract_sap_number_digits_only():
    assert extract_sap_number("1234567890") == "1234567890"


def test_extract_sap_number_strips_all_non_digits():
    assert extract_sap_number("abc-1234567890-xyz") == "1234567890"


# ── index_payments ────────────────────────────────────────────────────────────


def test_index_payments_maps_sap_to_path(tmp_path):
    payments_dir = tmp_path / "Remeses"
    payments_dir.mkdir()
    pdf = payments_dir / f"{SAP_ID}-P.pdf"
    create_blank_pdf(pdf)

    result = index_payments(payments_dir)

    assert SAP_ID in result
    assert result[SAP_ID] == pdf


def test_index_payments_skips_merged_files(tmp_path):
    payments_dir = tmp_path / "Remeses"
    payments_dir.mkdir()
    merged = payments_dir / f"{SAP_ID}-P_merged.pdf"
    create_blank_pdf(merged)

    result = index_payments(payments_dir)

    assert result == {}


def test_index_payments_skips_invalid_sap_length(tmp_path):
    payments_dir = tmp_path / "Remeses"
    payments_dir.mkdir()
    bad = payments_dir / "12345-P.pdf"  # only 5 digits
    create_blank_pdf(bad)

    result = index_payments(payments_dir)

    assert result == {}


def test_index_payments_empty_folder(tmp_path):
    payments_dir = tmp_path / "Remeses"
    payments_dir.mkdir()

    result = index_payments(payments_dir)

    assert result == {}


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
        with pytest.raises(ValueError, match="No SAP ID found"):
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


# ── merge_pdfs ────────────────────────────────────────────────────────────────


def test_merge_pdfs_creates_output_file(tmp_path):
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    output = tmp_path / "merged.pdf"
    create_blank_pdf(first)
    create_blank_pdf(second)

    merge_pdfs(first, second, output)

    assert output.exists()
    assert output.stat().st_size > 0


def test_merge_pdfs_output_has_two_pages(tmp_path):
    from pypdf import PdfReader

    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    output = tmp_path / "merged.pdf"
    create_blank_pdf(first)
    create_blank_pdf(second)

    merge_pdfs(first, second, output)

    reader = PdfReader(output)
    assert len(reader.pages) == 2


# ── cleanup_processed_files ───────────────────────────────────────────────────


def test_cleanup_processed_files_renames_payment(tmp_path):
    bill = tmp_path / f"F {SAP_ID}.pdf"
    bill.touch()
    payment = tmp_path / f"{SAP_ID}-P.pdf"
    payment.touch()

    cleanup_processed_files(bill, payment, delete_processed=False)

    assert (tmp_path / f"{SAP_ID}-P_merged.pdf").exists()
    assert bill.exists()  # not deleted when delete_processed=False


def test_cleanup_processed_files_deletes_bill_when_requested(tmp_path):
    bill = tmp_path / f"F {SAP_ID}.pdf"
    bill.touch()
    payment = tmp_path / f"{SAP_ID}-P.pdf"
    payment.touch()

    cleanup_processed_files(bill, payment, delete_processed=True)

    assert not bill.exists()


# ── rename_payments ───────────────────────────────────────────────────────────


def test_rename_payments_renames_pdf(tmp_path):
    payments_dir = tmp_path / "Remeses"
    payments_dir.mkdir()
    pdf = payments_dir / "some_payment_document.pdf"
    create_blank_pdf(pdf)

    with patch("justifactu.pdf.parse_sap_id_from_bill", return_value=SAP_ID):
        rename_payments(payments_dir)

    assert (payments_dir / f"{SAP_ID}-P.pdf").exists()
    assert not pdf.exists()


def test_rename_payments_skips_already_renamed(tmp_path):
    payments_dir = tmp_path / "Remeses"
    payments_dir.mkdir()
    already_renamed = payments_dir / f"{SAP_ID}-P.pdf"
    create_blank_pdf(already_renamed)

    with patch("justifactu.pdf.parse_sap_id_from_bill") as mock_parse:
        rename_payments(payments_dir)
        mock_parse.assert_not_called()


def test_rename_payments_skips_non_pdf(tmp_path):
    payments_dir = tmp_path / "Remeses"
    payments_dir.mkdir()
    txt_file = payments_dir / "document.txt"
    txt_file.touch()

    with patch("justifactu.pdf.parse_sap_id_from_bill") as mock_parse:
        rename_payments(payments_dir)
        mock_parse.assert_not_called()


def test_rename_payments_not_a_directory(tmp_path):
    not_a_dir = tmp_path / "file.pdf"
    create_blank_pdf(not_a_dir)

    # Should log a warning and return without raising
    rename_payments(not_a_dir)


# ── merge_bills_and_payments ──────────────────────────────────────────────────


def test_merge_bills_and_payments_success(billing_dirs):
    bills_dir, payments_dir, output_dir = billing_dirs

    bill = bills_dir / f"F {SAP_ID}.pdf"
    payment = payments_dir / f"{SAP_ID}-P.pdf"
    create_blank_pdf(bill)
    create_blank_pdf(payment)

    merge_bills_and_payments(bills_dir, payments_dir, output_dir)

    expected_subfolder = output_dir / f"{SAP_ID[:4]}_FACTURA+PAGAMENT"
    expected_output = expected_subfolder / f"{SAP_ID}_F_P.pdf"
    assert expected_output.exists()


def test_merge_bills_and_payments_invalid_bill_format_moved_to_qa(billing_dirs):
    bills_dir, payments_dir, output_dir = billing_dirs

    bad_bill = bills_dir / "INVALID_NAME.pdf"
    create_blank_pdf(bad_bill)

    merge_bills_and_payments(bills_dir, payments_dir, output_dir)

    qa_folder = output_dir / "QA_ERRORS"
    assert (qa_folder / "INVALID_NAME.pdf").exists()
    assert not bad_bill.exists()


def test_merge_bills_and_payments_no_matching_payment(billing_dirs):
    bills_dir, payments_dir, output_dir = billing_dirs

    bill = bills_dir / f"F {SAP_ID}.pdf"
    create_blank_pdf(bill)
    # No corresponding payment file

    # Should not raise; unmatched bill is logged as error
    merge_bills_and_payments(bills_dir, payments_dir, output_dir)

    expected_output = (
        output_dir / f"{SAP_ID[:4]}_FACTURA+PAGAMENT" / f"{SAP_ID}_F_P.pdf"
    )
    assert not expected_output.exists()


def test_merge_bills_and_payments_creates_output_folder(billing_dirs):
    bills_dir, payments_dir, output_dir = billing_dirs

    merge_bills_and_payments(bills_dir, payments_dir, output_dir)

    assert output_dir.exists()


def test_merge_bills_and_payments_delete_processed(billing_dirs):
    bills_dir, payments_dir, output_dir = billing_dirs

    bill = bills_dir / f"F {SAP_ID}.pdf"
    payment = payments_dir / f"{SAP_ID}-P.pdf"
    create_blank_pdf(bill)
    create_blank_pdf(payment)

    merge_bills_and_payments(bills_dir, payments_dir, output_dir, delete_processed=True)

    assert not bill.exists()
