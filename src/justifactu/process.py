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

from .bills import parse_bill_filename
from .custom_except import (
    MergingBillWithPaymentError,
    FileDeletionError,
    ParseSAPIdException,
)

from .defines import FolderName, FileSuffix
from .filesystem import list_dir, move_file, change_file_name, index_folder
from .logger import get_logger
from .payments import index_payments
from .pdf import merge_pdfs

log = get_logger(__name__)


def merge_bills_and_payments(
    bills_folder: Path,
    payments_folder: Path,
    merge_folder: Path,
    delete_processed: bool = False,
    sharepoint_url_map: dict[Path, str] | None = None,
) -> None:
    """Merges bills and payments and saves them into merge_folder"""

    merge_folder.mkdir(parents=True, exist_ok=True)
    payment_map = index_payments(index_folder(payments_folder))
    successful_payments: set[Path] = set()
    qa_folder = merge_folder / FolderName.QA_ERRORS
    qa_folder.mkdir(parents=True, exist_ok=True)

    # Process bills and look for matches
    for bill_path in list_dir(bills_folder):
        url = sharepoint_url_map.get(bill_path) if sharepoint_url_map else None
        url_suffix = f" | SharePoint: {url}" if url else ""

        if not bill_path.is_file() or bill_path.suffix.lower() != ".pdf":
            log.warning(
                f"Skipped bill file because it is not a PDF file: {bill_path}{url_suffix}",
                extra={"qa_report": True},
            )
            continue

        try:
            sap = parse_bill_filename(bill_path.stem)
        except ParseSAPIdException:
            move_file(bill_path, qa_folder)
            log.error(
                f"Failed to merge bill file {bill_path}: unexpected name format, moved to QA folder{url_suffix}",
                extra={"qa_report": True},
            )
            continue

        matched_payment: Path | None = payment_map.get(sap)

        if not matched_payment:
            log.error(f"No matching payment found for bill {bill_path}{url_suffix}")
            continue

        output_folder_name = f"{sap.year}{FolderName.YEAR_FOLDER_SUFFIX.value}"
        output_folder_path = merge_folder / output_folder_name
        output_folder_path.mkdir(parents=True, exist_ok=True)

        output_path = (
            output_folder_path / f"{sap}{FileSuffix.MERGED_BILL_PAYMENT.value}.pdf"
        )
        try:
            log.info(f"Merging {bill_path.name} with {matched_payment.name}...")
            merge_pdfs(bill_path, matched_payment, output_path)
            # TODO upload output path to sharepoint. Should it be per file or whole folder?
            successful_payments.add(matched_payment)
            cleanup_processed_files(bill_path, matched_payment, delete_processed)
        except MergingBillWithPaymentError as e:
            log.exception(f"Failed to process {bill_path.name}: {e}")


def cleanup_processed_files(
    bill_path: Path, matched_payment: Path, delete_processed: bool
) -> None:
    """Renames the payment file and optionally deletes the bill file"""
    new_name = f"{matched_payment.stem}{FileSuffix.PROCESSED_PAYMENT.value}"
    renamed_path = change_file_name(matched_payment, new_name)

    if renamed_path is None:
        log.error(f"Failed to rename processed payment file {matched_payment}")
    else:
        log.info(f"Renamed processed payment file {renamed_path.name}")

    if delete_processed:
        try:
            bill_path.unlink()
            log.info(f"Deleted: {bill_path.name}")
        except FileDeletionError as e:
            log.exception(f"Failed to delete {bill_path.name}: {e}")
