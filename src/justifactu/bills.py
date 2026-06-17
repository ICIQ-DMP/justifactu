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


from justifactu.logger import get_logger
from justifactu.filesystem import list_dir, move_file, change_file_name
from justifactu.SAP import SAP
from justifactu.pdf import merge_pdfs
from justifactu.payments import index_payments

log = get_logger(__name__)


def merge_bills_and_payments(
    bills_folder: Path,
    payments_folder: Path,
    merge_folder: Path,
    delete_processed: bool = False,
) -> None:
    """Merges bills and payments and saves them into merge_folder"""

    merge_folder.mkdir(parents=True, exist_ok=True)
    payment_map = index_payments(payments_folder)
    successful_payments: set[Path] = set()
    qa_folder = merge_folder / "QA_ERRORS"

    # Process bills and look for matches
    for bill_path in list_dir(bills_folder):
        if not bill_path.is_file() or bill_path.suffix.lower() != ".pdf":
            continue

        if not SAP.matches_bill_filename(bill_path.stem):
            move_file(bill_path, qa_folder)
            log.error(
                f"Failed to merge bill file {bill_path}: unexpected name format, moved to QA folder",
                extra={"qa_report": True},
            )
            continue

        sap = SAP.from_filename(bill_path.stem)
        matched_payment: Path | None = payment_map.get(str(sap))

        if not matched_payment:
            log.error(f"No matching payment found for bill {bill_path}")
            continue

        output_folder_name = f"{sap.year}_FACTURA+PAGAMENT"
        output_folder_path = merge_folder / output_folder_name
        output_folder_path.mkdir(parents=True, exist_ok=True)

        output_path = output_folder_path / f"{sap}_F_P.pdf"
        try:
            log.info(f"Merging {bill_path.name} with {matched_payment.name}...")
            merge_pdfs(bill_path, matched_payment, output_path)
            successful_payments.add(matched_payment)
            cleanup_processed_files(bill_path, matched_payment, delete_processed)
        except Exception as e:
            log.exception(f"Failed to process {bill_path.name}: {e}")

    unmatched_payments = set(payment_map.values()) - successful_payments
    for payment in unmatched_payments:
        log.error(f"No matching payment found for {payment.name}")


def cleanup_processed_files(
    bill_path: Path, matched_payment: Path, delete_processed: bool
) -> None:
    """Renames the payment file and optionally deletes the bill file"""
    new_name = f"{matched_payment.stem}_merged"
    renamed_path = change_file_name(matched_payment, new_name)

    if renamed_path is None:
        log.error(f"Failed to rename processed payment file {matched_payment}")
    else:
        log.info(f"Renamed processed payment file {renamed_path.name}")

    if delete_processed:
        try:
            bill_path.unlink()
            log.info(f"Deleted: {bill_path.name}")
        except Exception as e:
            log.error(f"Failed to delete {bill_path.name}: {e}")
