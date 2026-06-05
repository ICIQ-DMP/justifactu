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
import shutil
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from justifactu.filesystem import list_dir
from justifactu.logger import get_logger

log = get_logger(__name__)


def rename_payments(pdf_path: Path) -> None:
    """Renames the files from the payments folder"""
    root_path = Path(pdf_path)

    if not root_path.is_dir():
        log.warning(f"{pdf_path} is not a directory")
        return

    pattern = re.compile(r"\d{10}-P$")

    for entry in list(root_path.rglob("*")):

        if entry.is_dir():
            continue

        if pattern.search(entry.stem):
            continue

        if entry.suffix.lower() != ".pdf":
            log.warning(f"Skipping file {entry}: non-PDF file")
            continue

        try:
            log.info(f"Processing:{entry.name}...")

            sap_id = parse_sap_id_from_bill(entry)

            updated_entry = change_file_name(entry, sap_id + "-P")

            if not updated_entry:
                continue

            log.info(f"Processed: {updated_entry.name}")

        except ValueError:
            log.warning(f"Skipped {entry.name} due to invalid value")

        except Exception as e:
            log.exception(f"Unexpected error processing {entry.name}: {e}")


def copy_file(origin_path: Path, target_path: Path) -> None:
    """Copies a file to another location"""
    # Check to avoid overwriting a file.
    dest_file = target_path / origin_path.name if target_path.is_dir() else target_path

    if dest_file.exists():
        raise FileExistsError(f"Destination file already exists: {dest_file}")

    target_path.mkdir(parents=True, exist_ok=True)

    shutil.copy(origin_path, dest_file)

    log.info(f"Copied: {origin_path} into {target_path}")


def parse_sap_id_from_bill(pdf_path: Path) -> str:
    """Reads a PDF file to extract the SAP id"""
    query_str = r"Fra\.?\s+(\d{10})"
    pattern = re.compile(query_str, re.MULTILINE)

    reader = PdfReader(pdf_path)

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue

        match = pattern.search(text)
        if not match:
            continue

        return match.group(1)

    raise ValueError(f"No SAP ID found in {pdf_path}")


def change_file_name(file: Path, new_name: str) -> Path | None:
    """Changes the name of a file"""
    if not file.exists():
        log.warning(f"File not found at {file}")
        return None

    new_path = file.with_stem(f"{new_name}")

    try:
        file.rename(new_path)
        return new_path
    except FileExistsError:
        log.warning(f"A file named {new_path.name} already exists.")
        return None


def _extract_sap_number(filename: str) -> str:
    """Extracts the numeric SAP ID from a filename."""

    return re.sub(r"\D", "", filename)


def _index_payments(payments_folder: Path) -> dict[str, Path]:
    """Scans the payments folder and returns a mapping of SAP numbers to file paths."""
    payment_map: dict[str, Path] = {}

    for payment_path in payments_folder.rglob("*.pdf"):
        if not payment_path.is_file():
            continue

        if payment_path.stem.endswith("_merged"):
            log.info(f"Skipping {payment_path} because it is already merged")
            continue

        sap_number = _extract_sap_number(payment_path.name)

        if len(sap_number) != 10:
            log.warning(
                f"Skipping {payment_path.name}: SAP number has unexpected length ({len(sap_number)} digits)"
            )
            continue

        if not sap_number:
            log.warning(
                f"Skipping {payment_path.name}: not renamed properly / can't be parsed."
            )
            continue

        payment_map[sap_number] = payment_path

    return payment_map


def _merge_pdfs(first_pdf: Path, second_pdf: Path, output_path: Path) -> None:
    """Merges two PDF files into output_path"""
    writer = PdfWriter()
    writer.append(first_pdf)
    writer.append(second_pdf)

    with open(output_path, "wb") as f:
        writer.write(f)
    writer.close()


def _cleanup_processed_files(
    bill_path: Path, matched_payment: Path, delete_processed: bool
) -> None:
    """Renames the payment file and optionally deletes the bill file"""
    new_name = f"{matched_payment.stem}_merged"
    renamed_path = change_file_name(matched_payment, new_name)

    if renamed_path is None:
        log.error(f"Failed to rename processed payment file {matched_payment.name}")
    else:
        log.info(f"Renamed processed payment file {renamed_path.name}")

    if delete_processed:
        bill_path.unlink()
        log.info(f"Deleted: {bill_path.name}")


def merge_bills_and_payments(
    bills_folder: Path,
    payments_folder: Path,
    merge_folder: Path,
    delete_processed: bool = False,
) -> None:
    """Merges bills and payments and saves into merge_folder"""

    merge_folder.mkdir(parents=True, exist_ok=True)
    payment_map = _index_payments(payments_folder)
    successful_payments: set[Path] = set()

    # Process bills and look for matches
    for bill_path in list_dir(bills_folder):
        if not bill_path.is_file() or bill_path.suffix.lower() != ".pdf":
            continue

        bill_numbers = _extract_sap_number(bill_path.stem)
        matched_payment: Path | None = payment_map.get(bill_numbers)

        if not matched_payment:
            log.error("No matching payment found for bill")
            continue

        output_folder_name = f"{bill_numbers[:4]}_FACTURA+PAGAMENT"
        output_folder_path = merge_folder / output_folder_name
        output_folder_path.mkdir(parents=True, exist_ok=True)

        output_path = output_folder_path / f"{bill_numbers}_F_P.pdf"

        log.info(f"Merging {bill_path.name} with {matched_payment.name}...")
        _merge_pdfs(bill_path, matched_payment, output_path)
        successful_payments.add(matched_payment)
        _cleanup_processed_files(bill_path, matched_payment, delete_processed)

    unmatched_payments = set(payment_map.values()) - successful_payments
    for payment in unmatched_payments:
        log.error(f"No matching payment found for {payment.name}")

    pass
