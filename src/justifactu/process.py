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
from typing import Callable

from .SAP_ID import SAP_ID
from .bills import parse_bill_filename
from .custom_except import (
    MergingBillWithPaymentError,
    ParseSAPIdException,
)

from .defines import FolderName, FileSuffix, Phase
from .filesystem import list_dir, index_folder, change_file_name
from .logger import get_logger
from .payments import index_payments, rename_payments
from .pdf import merge_pdfs

log = get_logger(__name__)


def merge_bills_and_payments(
    bills_folder: Path,
    payments_folder: Path,
    merge_folder: Path,
    delete_processed: bool = False,
    freshly_renamed_payments: dict[SAP_ID, Path] | None = None,
) -> None:
    """Merges bills and payments and saves them into merge_folder"""

    merge_folder.mkdir(parents=True, exist_ok=True)
    payment_map = {
        **index_payments(index_folder(payments_folder)),
        **(freshly_renamed_payments or {}),
    }
    successful_payments: set[Path] = set()
    qa_folder = merge_folder / FolderName.QA_ERRORS
    qa_folder.mkdir(parents=True, exist_ok=True)

    # Process bills and look for matches
    for bill_path in list_dir(bills_folder):
        if not bill_path.is_file() or bill_path.suffix.lower() != ".pdf":
            log.warning(
                f"Skipped bill file because it is not a PDF file: {bill_path}",
                extra={"qa_report": True},
            )
            continue

        try:
            sap = parse_bill_filename(bill_path.stem)
        except ParseSAPIdException:
            log.error(
                f"Failed to merge bill file {bill_path}: unexpected name format.",
                extra={"qa_report": True},
            )
            continue

        matched_payment: Path | None = payment_map.get(sap)

        if not matched_payment:
            log.error(f"No matching payment found for bill {bill_path}")
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

            cleanup_processed_files(
                bill_path,
                matched_payment,
                delete_processed,
            )
        except MergingBillWithPaymentError as e:
            log.exception(f"Failed to process {bill_path.name}: {e}")


def cleanup_processed_files(
    bill_path: Path,
    matched_payment: Path,
    delete_processed: bool,
) -> None:
    """Renames the payment file and optionally deletes the bill file"""
    new_name = f"{matched_payment.stem}{FileSuffix.PROCESSED_PAYMENT.value}"
    try:
        change_file_name(matched_payment, new_name)
        log.info(f"Renamed processed payment file: {matched_payment.name}")

        if delete_processed:
            bill_path.unlink(missing_ok=True)
            log.info(f"Deleted: {bill_path.name}")

    except FileNotFoundError as e:
        log.error(
            f"Failed to rename processed payment file {matched_payment.name}: {e}"
        )


def mock_phase3() -> None:
    log.error("Mocking phase 3 successful! :D")


def _phase_folders(input_folder: Path) -> tuple[Path, Path, Path]:
    bills_folder = input_folder / FolderName.BILLS_INPUT.value
    payments_folder = input_folder / FolderName.PAYMENTS_INPUT.value
    bills_plus_payments_folder = (
        input_folder.parent / FolderName.OUTPUT.value / FolderName.MERGED_OUTPUT.value
    )
    return bills_folder, payments_folder, bills_plus_payments_folder


def _build_phase_map(input_folder: Path) -> dict[Phase, Callable[[], None]]:
    bills_folder, payments_folder, bills_plus_payments_folder = _phase_folders(
        input_folder
    )

    def _run_phase_1() -> None:
        rename_payments(payments_folder)

    def _run_phase_2() -> None:
        merge_bills_and_payments(
            bills_folder,
            payments_folder,
            bills_plus_payments_folder,
            delete_processed=True,
        )

    return {
        Phase.PHASE_1: _run_phase_1,
        Phase.PHASE_2: _run_phase_2,
        Phase.PHASE_3: mock_phase3,
    }


def run_phase(phase: Phase, input_folder: Path) -> None:
    _build_phase_map(input_folder)[phase]()


FULL_RUN_PHASES: tuple[Phase, ...] = (Phase.PHASE_1, Phase.PHASE_2)


def run_all_phases(input_folder: Path) -> None:
    phase_map = _build_phase_map(input_folder)
    for phase in FULL_RUN_PHASES:
        phase_map[phase]()
