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
    root_path = Path(pdf_path)

    if not root_path.is_dir():
        log.warning(f"{pdf_path} is not a directory")
        return

    for entry in list(root_path.rglob("*")):

        if entry.is_dir():
            continue
        if entry.stem.endswith(r"\d{10}-P"):
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
    """Copy a file to another location"""
    # Check to avoid overwriting a file.
    dest_file = target_path / origin_path.name if target_path.is_dir() else target_path

    # Changed from using except to raise for Exceptions
    if dest_file.exists():
        raise FileExistsError(f"Destination file already exists: {dest_file}")

    target_path.mkdir(parents=True, exist_ok=True)

    shutil.copy(origin_path, dest_file)

    log.info(f"Copied: {origin_path} into {target_path}")


def parse_sap_id_from_bill(pdf_path: Path) -> str:
    # Regex query using a capture group to extract the SAP number
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

        # match.group(1) targets only the parenthesis
        return match.group(1)

    raise ValueError(f"No SAP ID found in {pdf_path}")


def change_file_name(file: Path, new_name: str) -> Path | None:
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


# TODO rename_payments: se li passa la carpeta de remeses i recórrer tots els fitxers i canviar el nom.
# Posar flag al log si no es pot canviar el nom
# TODO recórrer tots els pagaments de Remeses i si tenen un nom SAP, buscar la factura corresponent, fusionar-la,
# deixar-la a la carpeta corresponent i si no, apuntar un flag al log.


def merge_bills_and_payments(
    bills_folder: Path,
    payments_folder: Path,
    merge_folder: Path,
    delete_processed: bool = False,
) -> None:
    merge_folder.mkdir(parents=True, exist_ok=True)

    payment_map: dict[str, Path] = {}
    successful_payments: set[Path] = set()
    # Index all payments by their SAP number only
    for payment_path in list_dir(payments_folder):
        if not payment_path.is_file() or payment_path.suffix.lower() != ".pdf":
            log.warning(f"Skipping {payment_path} because it's not a PDF file")
            continue

        payment_numbers = re.sub(r"\D", "", payment_path.stem)

        if not payment_numbers:
            log.warning(
                f"The payment number from {payment_path} can't be parsed. Skipping."
            )
            continue

        payment_map[payment_numbers] = payment_path

    # Check if SAP number matches bills and merge if true
    for bill_path in list_dir(bills_folder):
        if not bill_path.is_file() or bill_path.suffix.lower() != ".pdf":
            continue

        bill_numbers = re.sub(r"\D", "", bill_path.stem)
        matched_payment: Path | None = payment_map.get(bill_numbers)

        if matched_payment:
            output_folder = bill_numbers[:4] + "_FACTURA+PAGAMENT"
            output_path = merge_folder / output_folder / f"{bill_numbers}_F_P.pdf"
            writer = PdfWriter()

            log.info(f"Merging: {bill_path.name} with {matched_payment}...")

            writer.append(bill_path)
            writer.append(matched_payment)

            with open(output_path, "wb") as f:
                writer.write(f)
            writer.close()

            successful_payments.add(matched_payment)

            new_name = f"{matched_payment.stem}_merged"
            renamed_path = change_file_name(matched_payment, new_name)

            if renamed_path is None:
                log.error(
                    f"Failed to rename processed payment file {matched_payment.name}"
                )
            else:
                log.info(f"Renamed processed payment file {renamed_path.name}")

            if delete_processed:
                bill_path.unlink()
                log.info(f"Deleted: {bill_path.name}")
        else:
            log.error(f"No matching payment for {bill_path.name}")

    pass
