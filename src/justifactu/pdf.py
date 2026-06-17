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

import re
from pathlib import Path

from pypdf import PdfWriter

from justifactu.filesystem import list_dir
from justifactu.filesystem import move_file
from justifactu.filesystem import change_file_name
from justifactu.bills import parse_sap_id_from_bill
from justifactu.logger import get_logger

log = get_logger(__name__)


def extract_sap_number(filename: str) -> str:
    """Extracts the numeric SAP ID from a filename."""
    return re.sub(
        r"\D", "", filename
    )  # TODO: build specialized class SAP that know how to parse this.


# TODO: this func should go into a specific file, this is not related to pdfs, but to payments instead (bills.pdf ?)
def index_payments(payments_folder: Path) -> dict[str, Path]:
    """Scans the payments folder and returns a mapping of SAP numbers to file paths."""
    payment_map: dict[str, Path] = {}

    for payment_path in payments_folder.rglob("*.pdf"):
        if not payment_path.is_file():
            continue

        if payment_path.stem.endswith("_merged"):
            log.info(f"Skipping {payment_path} because it is already merged")
            continue

        sap_number = extract_sap_number(payment_path.name)

        if len(sap_number) != 10:
            log.warning(
                f"Skipping {payment_path.name}: SAP number has unexpected length ({len(sap_number)} digits)"
            )
            continue

        payment_map[sap_number] = payment_path

    return payment_map


def merge_pdfs(first_pdf: Path, second_pdf: Path, output_path: Path) -> None:
    """Merges two PDF files into output_path"""
    writer = PdfWriter()
    writer.append(first_pdf)
    writer.append(second_pdf)

    with open(output_path, "wb") as f:
        writer.write(f)
        writer.close()


# TODO: this func should go into a specific file, this is not related to pdfs, but to payments instead (bills.pdf ?)
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


def rename_payments(pdf_path: Path) -> None:
    """Renames the files from the payments folder"""
    if not pdf_path.is_dir():
        log.warning(f"{pdf_path} is not a directory")
        return

    pattern = re.compile(r"\d{10}-P$")

    for entry in list(pdf_path.rglob("*")):
        if entry.is_dir():
            continue

        if pattern.search(entry.stem):
            continue

        if entry.suffix.lower() != ".pdf":
            log.warning(f"Skipping file {entry}: non-PDF file")
            continue

        try:
            log.info(f"Renaming: {entry.name}...")

            sap_id = parse_sap_id_from_bill(entry)

            updated_entry = change_file_name(entry, sap_id + "-P")

            if not updated_entry:
                continue

            log.info(f"File name changed to: {updated_entry.name}")

        except ValueError:
            print("---DEBUG: Python entered the block---")
            log.warning(f"Skipped {entry.name} due to invalid value")

        except Exception as e:
            log.exception(f"Unexpected error processing {entry.name}: {e}")


# TODO: this func should go into a specific file, this is not related to pdfs, but to the general process instead
# (main.py ?)
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
    expected_name = re.compile(
        r"F\s\d{10}"
    )  # TODO: delegate into SAP id class, look at NAF class in justicier

    # Process bills and look for matches
    for bill_path in list_dir(bills_folder):
        if not bill_path.is_file() or bill_path.suffix.lower() != ".pdf":
            continue

        if not expected_name.fullmatch(bill_path.stem):
            move_file(bill_path, qa_folder)
            log.error(
                f"Failed to merge bill file {bill_path}: unexpected name format, moved to QA folder",
                extra={"qa_report": True},
            )
            continue

        bill_numbers = extract_sap_number(bill_path.stem)
        matched_payment: Path | None = payment_map.get(bill_numbers)

        if not matched_payment:
            log.error(f"No matching payment found for bill {bill_path}")
            continue
        # TODO: This means that bill_numbers[:4] follow a specific format and the regexp can be more specific
        output_folder_name = f"{bill_numbers[:4]}_FACTURA+PAGAMENT"
        output_folder_path = merge_folder / output_folder_name
        output_folder_path.mkdir(parents=True, exist_ok=True)

        output_path = output_folder_path / f"{bill_numbers}_F_P.pdf"
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
