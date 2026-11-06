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

from unittest.mock import patch

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

from conftest import create_blank_pdf
from justifactu.SAP_ID import SAP_ID, pattern, parse_sap_id_from_string
from justifactu.custom_except import (
    MergingBillWithPaymentError,
    NotAPaymentFileError,
    ParseSAPIdException,
)
from justifactu.defines import FileSuffix, FolderName, Metric
from justifactu.payments import (
    index_payments,
    rename_payment,
)
from justifactu.process import (
    cleanup_processed_files,
    merge_bills_and_payments,
    rename_payments,
)
from justifactu.filesystem import index_folder
from justifactu.pdf import (
    merge_pdfs,
    HighlightBox,
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
    payments_dir = tmp_path / FolderName.PAYMENTS.value
    payments_dir.mkdir()
    pdf = payments_dir / f"{id_sap_instance}-P.pdf"
    create_blank_pdf(pdf)

    result = index_payments(index_folder(payments_dir))

    assert id_sap_instance in result
    assert result[id_sap_instance] == pdf


def test_index_payments_skips_merged_files(tmp_path):
    payments_dir = tmp_path / FolderName.PAYMENTS.value
    payments_dir.mkdir()
    merged = payments_dir / f"{pattern}-P_merged.pdf"
    create_blank_pdf(merged)

    result = index_payments(index_folder(payments_dir))

    assert result == {}


def test_index_payments_skips_invalid_sap_length(tmp_path):
    payments_dir = tmp_path / FolderName.PAYMENTS.value
    payments_dir.mkdir()
    bad = payments_dir / "12345-P.pdf"  # only 5 digits
    create_blank_pdf(bad)

    result = index_payments(index_folder(payments_dir))

    assert result == {}


def test_index_payments_empty_folder(tmp_path):
    payments_dir = tmp_path / FolderName.PAYMENTS.value
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


def test_merge_pdfs_raises_and_leaves_no_output_on_corrupt_input(tmp_path):
    first = tmp_path / "first.pdf"
    corrupt = tmp_path / "corrupt.pdf"
    output = tmp_path / "merged.pdf"
    create_blank_pdf(first)
    corrupt.write_bytes(b"not a pdf")

    with pytest.raises(MergingBillWithPaymentError):
        merge_pdfs(first, corrupt, output)

    assert not output.exists()


# ── cleanup_processed_files ───────────────────────────────────────────────────


def test_cleanup_processed_files_renames_payment(tmp_path):
    bill = tmp_path / f"F {id_sap_instance}.pdf"
    bill.touch()
    payment = tmp_path / f"{id_sap_instance}-P.pdf"
    payment.touch()

    cleanup_processed_files(bill, payment, delete_processed=False)

    renamed_payment = (
        tmp_path / f"{id_sap_instance}-P{FileSuffix.PROCESSED_PAYMENT.value}.pdf"
    )
    assert renamed_payment.exists()
    assert not payment.exists()
    assert bill.exists()


def test_cleanup_processed_files_deletes_bill_when_requested(tmp_path):
    bill = tmp_path / f"F {id_sap_instance}.pdf"
    bill.touch()
    payment = tmp_path / f"{id_sap_instance}-P.pdf"
    payment.touch()

    cleanup_processed_files(bill, payment, delete_processed=True)

    assert not bill.exists()


# ── rename_payments ───────────────────────────────────────────────────────────


def test_rename_payments_renames_pdf(tmp_path):
    payments_dir = tmp_path / FolderName.PAYMENTS.value
    payments_dir.mkdir()
    pdf = payments_dir / "some_payment_document.pdf"
    create_blank_pdf(pdf)

    with patch(
        "justifactu.payments.parse_sap_id_from_payment",
        return_value=str(id_sap_instance),
    ):
        metrics = rename_payments(payments_dir)

    renamed_pdf = payments_dir / f"{id_sap_instance}-P.pdf"
    assert renamed_pdf.exists()
    assert not pdf.exists()
    assert sum(metrics.values()) == 0


def test_rename_payments_skips_already_renamed(tmp_path):
    payments_dir = tmp_path / FolderName.PAYMENTS.value
    payments_dir.mkdir()
    already_renamed = payments_dir / f"{id_sap_instance}-P.pdf"
    create_blank_pdf(already_renamed)

    with patch("justifactu.payments.parse_sap_id_from_payment") as mock_parse:
        rename_payments(payments_dir)
        mock_parse.assert_not_called()


def test_rename_payments_skips_non_pdf(tmp_path):
    payments_dir = tmp_path / FolderName.PAYMENTS.value
    payments_dir.mkdir()
    txt_file = payments_dir / "document.txt"
    txt_file.touch()

    with patch("justifactu.payments.parse_sap_id_from_payment") as mock_parse:
        rename_payments(payments_dir)
        mock_parse.assert_not_called()


def test_rename_payments_counts_non_pdf_files(tmp_path):
    payments_dir = tmp_path / FolderName.PAYMENTS.value
    payments_dir.mkdir()
    (payments_dir / "document.txt").touch()
    (payments_dir / "Thumbs.db").touch()

    metrics = rename_payments(payments_dir)

    assert metrics[Metric.TRASH_FILES] == 2
    assert metrics[Metric.UNPARSEABLE_PAYMENTS] == 0


def test_rename_payments_counts_unparseable_pdfs(tmp_path):
    payments_dir = tmp_path / FolderName.PAYMENTS.value
    payments_dir.mkdir()
    create_blank_pdf(payments_dir / "no_sap_id.pdf")

    with patch(
        "justifactu.payments.parse_sap_id_from_payment",
        side_effect=ParseSAPIdException("no SAP ID"),
    ):
        metrics = rename_payments(payments_dir)

    assert metrics[Metric.UNPARSEABLE_PAYMENTS] == 1
    assert metrics[Metric.TRASH_FILES] == 0


def test_rename_payments_missing_folder_returns_no_metrics(tmp_path):
    assert rename_payments(tmp_path / "missing") == {}


# ── rename_payment ────────────────────────────────────────────────────────────


def test_rename_payment_returns_new_path(tmp_path):
    pdf = tmp_path / "bank_statement.pdf"
    create_blank_pdf(pdf)

    with patch(
        "justifactu.payments.parse_sap_id_from_payment",
        return_value=str(id_sap_instance),
    ):
        renamed = rename_payment(pdf)

    assert renamed == tmp_path / f"{id_sap_instance}-P.pdf"
    assert renamed.exists()


def test_rename_payment_raises_for_non_pdf(tmp_path):
    txt_file = tmp_path / "document.txt"
    txt_file.touch()

    with pytest.raises(NotAPaymentFileError):
        rename_payment(txt_file)

    assert txt_file.exists()


def test_rename_payment_raises_when_sap_id_missing(tmp_path):
    pdf = tmp_path / "bank_statement.pdf"
    create_blank_pdf(pdf)

    with pytest.raises(ParseSAPIdException):
        rename_payment(pdf)

    assert pdf.exists()


# ── merge_bills_and_payments ──────────────────────────────────────────────────


def test_merge_bills_and_payments_success(billing_dirs):
    bills_dir, payments_dir, output_dir = billing_dirs

    bill = bills_dir / f"F {id_sap_instance}.pdf"
    payment = payments_dir / f"{id_sap_instance}-P.pdf"
    create_blank_pdf(bill)
    create_blank_pdf(payment)

    merge_bills_and_payments(bills_dir, payments_dir, output_dir)

    expected_subfolder = (
        output_dir / f"{id_sap_instance.year}{FileSuffix.YEAR_FOLDER_SUFFIX.value}"
    )
    expected_output = (
        expected_subfolder
        / f"{id_sap_instance}{FileSuffix.MERGED_BILL_PAYMENT.value}.pdf"
    )
    assert expected_output.exists()


def test_merge_bills_and_payments_counts_merges(billing_dirs):
    bills_dir, payments_dir, output_dir = billing_dirs
    create_blank_pdf(bills_dir / f"F {id_sap_instance}.pdf")
    create_blank_pdf(payments_dir / f"{id_sap_instance}-P.pdf")
    create_blank_pdf(bills_dir / "F 2034000001.pdf")  # no payment: not a merge

    metrics = merge_bills_and_payments(bills_dir, payments_dir, output_dir)

    assert metrics[Metric.PAYMENT_MERGES] == 1
    assert metrics[Metric.UNMATCHED_BILLS] == 0  # decided by phase 3, not here


def test_merge_bills_and_payments_counts_failed_merge_and_keeps_files(billing_dirs):
    bills_dir, payments_dir, output_dir = billing_dirs
    bill = bills_dir / f"F {id_sap_instance}.pdf"
    payment = payments_dir / f"{id_sap_instance}-P.pdf"
    create_blank_pdf(bill)
    payment.write_bytes(b"not a pdf")

    metrics = merge_bills_and_payments(
        bills_dir, payments_dir, output_dir, delete_processed=True
    )

    assert metrics[Metric.FAILED_MERGES] == 1
    assert metrics[Metric.PAYMENT_MERGES] == 0
    assert bill.exists()
    assert payment.exists()  # not renamed to _merged


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


# ── merge_pdfs highlights ────────────────────────────────────────────────────


def _highlight_rects(pdf_path) -> dict[int, list[list[float]]]:
    """Page index -> rects of every /Highlight annotation on that page."""
    rects: dict[int, list[list[float]]] = {}
    for index, page in enumerate(PdfReader(pdf_path).pages):
        for annotation in page.get("/Annots", []):
            annotation = annotation.get_object()
            if annotation["/Subtype"] == "/Highlight":
                rects.setdefault(index, []).append(
                    [round(float(v), 2) for v in annotation["/Rect"]]
                )
    return rects


def _two_page_pdf(path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    with open(path, "wb") as f:
        writer.write(f)


def test_merge_pdfs_without_highlights_adds_no_annotations(tmp_path):
    first = tmp_path / "bill.pdf"
    second = tmp_path / "statement.pdf"
    output = tmp_path / "merged.pdf"
    create_blank_pdf(first)
    create_blank_pdf(second)

    merge_pdfs(first, second, output)

    assert _highlight_rects(output) == {}


def test_merge_pdfs_highlights_box_on_second_pdf_page(tmp_path):
    bill = tmp_path / "bill.pdf"
    statement = tmp_path / "statement.pdf"
    output = tmp_path / "merged.pdf"
    create_blank_pdf(bill)  # 1 page
    _two_page_pdf(statement)
    box = HighlightBox(page=1, x0=40.0, top=134.0, x1=475.0, bottom=144.0)

    merge_pdfs(bill, statement, output, highlights=[box])

    # statement page 1 is output page 2; y is flipped from the 792pt page top,
    # with 1pt of padding on every side
    assert _highlight_rects(output) == {2: [[39.0, 647.0, 476.0, 659.0]]}
    annotation = PdfReader(output).pages[2]["/Annots"][0].get_object()
    assert [float(c) for c in annotation["/C"]] == [1.0, 1.0, 0.0]  # yellow


def test_merge_pdfs_highlight_follows_shifted_mediabox(tmp_path):
    bill = tmp_path / "bill.pdf"
    statement = tmp_path / "statement.pdf"
    output = tmp_path / "merged.pdf"
    create_blank_pdf(bill)
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    page.mediabox = RectangleObject([10, 20, 622, 812])
    with open(statement, "wb") as f:
        writer.write(f)
    box = HighlightBox(page=0, x0=40.0, top=134.0, x1=475.0, bottom=144.0)

    merge_pdfs(bill, statement, output, highlights=[box])

    assert _highlight_rects(output) == {1: [[49.0, 667.0, 486.0, 679.0]]}
