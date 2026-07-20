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
from requests.exceptions import HTTPError

from .bills import parse_bill_filename
from .custom_except import (
    MergingBillWithPaymentError,
    ParseSAPIdException,
)

from .defines import FolderName, FileSuffix
from .filesystem import list_dir, index_folder
from .logger import get_logger
from .payments import index_payments
from .pdf import merge_pdfs
from .sharepoint import rename_file_remote, delete_file_remote
from .token_manager import TokenManager

log = get_logger(__name__)


def merge_bills_and_payments(
    bills_folder: Path,
    payments_folder: Path,
    merge_folder: Path,
    delete_processed: bool = False,
    sharepoint_url_map: dict[Path, str] | None = None,
    token_manager: TokenManager | None = None,
    drive_id: str | None = None,
    remote_bills_folder: Path | None = None,
    remote_payments_folder: Path | None = None,
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
            log.error(
                f"Failed to merge bill file {bill_path}: unexpected name format. {url_suffix}",
                extra={"qa_report": True},
            )
            continue

        matched_payment: Path | None = payment_map.get(sap)

        if not matched_payment:
            log.error(f"No matching payment found for bill {bill_path}{url_suffix}")
            continue

        output_folder_name = sap.year + FolderName.YEAR_FOLDER_SUFFIX.value
        output_folder_path = merge_folder / output_folder_name
        output_folder_path.mkdir(parents=True, exist_ok=True)

        output_path = (
            output_folder_path / f"{sap}{FileSuffix.MERGED_BILL_PAYMENT.value}.pdf"
        )
        try:
            log.info(f"Merging {bill_path.name} with {matched_payment.name}...")
            merge_pdfs(bill_path, matched_payment, output_path)
            successful_payments.add(matched_payment)

            payment_relative_dir = matched_payment.parent.relative_to(payments_folder)
            payment_remote_folder = (
                remote_payments_folder / payment_relative_dir
                if remote_payments_folder is not None
                else None
            )
            bill_relative_dir = bill_path.parent.relative_to(bills_folder)
            bill_remote_folder = (
                remote_bills_folder / bill_relative_dir
                if remote_bills_folder is not None
                else None
            )

            cleanup_processed_files(
                bill_path,
                matched_payment,
                delete_processed,
                token_manager,
                drive_id,
                payment_remote_folder,
                bill_remote_folder,
            )
        except MergingBillWithPaymentError as e:
            log.exception(f"Failed to process {bill_path.name}: {e}")


def cleanup_processed_files(
    bill_path: Path,
    matched_payment: Path,
    delete_processed: bool,
    token_manager: TokenManager | None = None,
    drive_id: str | None = None,
    payment_remote_folder: Path | None = None,
    bill_remote_folder: Path | None = None,
) -> None:
    """Renames the payment file and optionally deletes the bill file"""
    new_name = f"{matched_payment.stem}{FileSuffix.PROCESSED_PAYMENT.value}"
    try:
        rename_file_remote(
            matched_payment, new_name, token_manager, drive_id, payment_remote_folder
        )
        log.info(f"Renamed processed payment file: {matched_payment.name}")

        if delete_processed:
            try:
                delete_file_remote(
                    bill_path, token_manager, drive_id, bill_remote_folder
                )
                log.info(f"Deleted: {bill_path.name}")
            except HTTPError as e:
                log.exception(f"Failed to delete {bill_path.name}: {e}")

    except HTTPError as e:
        log.error(f"Failed to rename processed payment file {matched_payment}: {e}")
