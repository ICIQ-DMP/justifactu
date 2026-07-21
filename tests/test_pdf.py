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

from unittest.mock import patch, MagicMock

from conftest import create_blank_pdf
from justifactu.SAP_ID import SAP_ID, pattern, parse_sap_id_from_string
from justifactu.defines import FileSuffix, FolderName
from justifactu.payments import (
    index_payments,
    rename_payments,
)
from justifactu.process import (
    cleanup_processed_files,
    merge_bills_and_payments,
)
from justifactu.filesystem import index_folder
from justifactu.pdf import (
    merge_pdfs,
)

id_sap_instance = SAP_ID("2034567890")


# ── extract_sap_number ────────────────────────────────────────────────────────


def test_extract_sap_number_from_payment_filename():
    assert parse_sap_id_from_string("2034567890-P") == SAP_ID("2034567890")


def test_extract_sap_number_from_bill_filename():
    assert parse_sap_id_from_string("F 2034567890") == SAP_ID("2034567890")


def test_extract_sap_number_digits_only():
    assert parse_sap_id_from_string("2034567890") == SAP_ID("2034567890")


def test_extract_sap_number_strips_all_non_digits():
    assert parse_sap_id_from_string("abc-2034567890-xyz") == SAP_ID("2034567890")


# ── index_payments ────────────────────────────────────────────────────────────


def test_index_payments_maps_sap_to_path(tmp_path):
    payments_dir = tmp_path / "Remeses"
    payments_dir.mkdir()
    pdf = payments_dir / f"{id_sap_instance}-P.pdf"
    create_blank_pdf(pdf)

    result = index_payments(index_folder(payments_dir))

    assert id_sap_instance in result
    assert result[id_sap_instance] == pdf


def test_index_payments_skips_merged_files(tmp_path):
    payments_dir = tmp_path / "Remeses"
    payments_dir.mkdir()
    merged = payments_dir / f"{pattern}-P_merged.pdf"
    create_blank_pdf(merged)

    result = index_payments(index_folder(payments_dir))

    assert result == {}


def test_index_payments_skips_invalid_sap_length(tmp_path):
    payments_dir = tmp_path / "Remeses"
    payments_dir.mkdir()
    bad = payments_dir / "12345-P.pdf"  # only 5 digits
    create_blank_pdf(bad)

    result = index_payments(index_folder(payments_dir))

    assert result == {}


def test_index_payments_empty_folder(tmp_path):
    payments_dir = tmp_path / "Remeses"
    payments_dir.mkdir()

    result = index_payments(index_folder(payments_dir))

    assert result == {}


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


@patch("justifactu.process.rename_file_remote")
def test_cleanup_processed_files_renames_payment(mock_rename, tmp_path):
    bill = tmp_path / f"F {id_sap_instance}.pdf"
    bill.touch()
    payment = tmp_path / f"{id_sap_instance}-P.pdf"
    payment.touch()

    cleanup_processed_files(
        bill,
        payment,
        delete_processed=False,
        token_manager=MagicMock(),
        drive_id="drive-id",
        payment_remote_folder=tmp_path,
    )

    mock_rename.assert_called_once_with(
        payment,
        f"{id_sap_instance}-P{FileSuffix.PROCESSED_PAYMENT.value}",
        mock_rename.call_args.args[2],
        "drive-id",
        tmp_path,
    )
    assert bill.exists()


@patch("justifactu.process.delete_file_remote")
@patch("justifactu.process.rename_file_remote")
def test_cleanup_processed_files_deletes_bill_when_requested(
    mock_rename, mock_delete, tmp_path
):
    bill = tmp_path / f"F {id_sap_instance}.pdf"
    bill.touch()
    payment = tmp_path / f"{id_sap_instance}-P.pdf"
    payment.touch()

    cleanup_processed_files(
        bill,
        payment,
        delete_processed=True,
        token_manager=MagicMock(),
        drive_id="drive-id",
        payment_remote_folder=tmp_path,
        bill_remote_folder=tmp_path,
    )

    mock_delete.assert_called_once_with(
        bill, mock_delete.call_args.args[1], "drive-id", tmp_path
    )


# ── rename_payments ───────────────────────────────────────────────────────────


@patch("justifactu.payments.rename_file_remote")
def test_rename_payments_renames_pdf(mock_rename, tmp_path):
    payments_dir = tmp_path / "Remeses"
    payments_dir.mkdir()
    pdf = payments_dir / "some_payment_document.pdf"
    create_blank_pdf(pdf)

    with patch(
        "justifactu.payments.parse_sap_id_from_bill", return_value=id_sap_instance
    ):
        rename_payments(
            payments_dir,
            token_manager=MagicMock(),
            drive_id="drive-id",
            remote_folder=payments_dir,
        )

    mock_rename.assert_called_once_with(
        pdf,
        f"{id_sap_instance}-P",
        mock_rename.call_args.args[2],
        "drive-id",
        payments_dir,
    )


def test_rename_payments_skips_already_renamed(tmp_path):
    payments_dir = tmp_path / "Remeses"
    payments_dir.mkdir()
    already_renamed = payments_dir / f"{id_sap_instance}-P.pdf"
    create_blank_pdf(already_renamed)

    with patch("justifactu.bills.parse_sap_id_from_bill") as mock_parse:
        rename_payments(payments_dir)
        mock_parse.assert_not_called()


def test_rename_payments_skips_non_pdf(tmp_path):
    payments_dir = tmp_path / "Remeses"
    payments_dir.mkdir()
    txt_file = payments_dir / "document.txt"
    txt_file.touch()

    with patch("justifactu.bills.parse_sap_id_from_bill") as mock_parse:
        rename_payments(payments_dir)
        mock_parse.assert_not_called()


# ── merge_bills_and_payments ──────────────────────────────────────────────────


def test_merge_bills_and_payments_success(billing_dirs):
    bills_dir, payments_dir, output_dir = billing_dirs

    bill = bills_dir / f"F {id_sap_instance}.pdf"
    payment = payments_dir / f"{id_sap_instance}-P.pdf"
    create_blank_pdf(bill)
    create_blank_pdf(payment)

    merge_bills_and_payments(bills_dir, payments_dir, output_dir)

    expected_subfolder = (
        output_dir / f"{id_sap_instance.year}{FolderName.YEAR_FOLDER_SUFFIX.value}"
    )
    expected_output = (
        expected_subfolder
        / f"{id_sap_instance}{FileSuffix.MERGED_BILL_PAYMENT.value}.pdf"
    )
    assert expected_output.exists()


def test_merge_bills_and_payments_no_matching_payment(billing_dirs):
    bills_dir, payments_dir, output_dir = billing_dirs

    bill = bills_dir / f"F {id_sap_instance}.pdf"
    create_blank_pdf(bill)
    # No corresponding payment file

    # Should not raise; unmatched bill is logged as error
    merge_bills_and_payments(bills_dir, payments_dir, output_dir)

    expected_output = (
        output_dir
        / f"{id_sap_instance.year}_FACTURA+PAGAMENT"
        / f"{id_sap_instance}_F_P.pdf"
    )
    assert not expected_output.exists()


def test_merge_bills_and_payments_creates_output_folder(billing_dirs):
    bills_dir, payments_dir, output_dir = billing_dirs

    merge_bills_and_payments(bills_dir, payments_dir, output_dir)

    assert output_dir.exists()


@patch("justifactu.process.cleanup_processed_files")
def test_merge_bills_and_payments_delete_processed(mock_cleanup, billing_dirs):
    bills_dir, payments_dir, output_dir = billing_dirs

    bill = bills_dir / f"F {id_sap_instance}.pdf"
    payment = payments_dir / f"{id_sap_instance}-P.pdf"
    create_blank_pdf(bill)
    create_blank_pdf(payment)

    merge_bills_and_payments(bills_dir, payments_dir, output_dir, delete_processed=True)

    assert mock_cleanup.call_args.args[2] is True  # delete_processed passed through
