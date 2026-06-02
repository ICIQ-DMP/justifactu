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


def recursive_name_change(pdf_path: Path) -> None:
    root_path = Path(pdf_path)

    if not root_path.is_dir():
        print(f"WARNING: {pdf_path} is not a directory")
        return

    for entry in root_path.rglob("*"):

        if entry.is_dir():
            continue

        if entry.stem.endswith("-P"):
            continue

        if entry.suffix != ".pdf":
            print(f"Skipping file {entry}: non-PDF file")
            continue

        try:
            print(f"Processing:{entry.name}...")

            sap_id = parse_sap_id_from_bill(entry)

            change_payment_name(entry, sap_id)

            # copy_pdf(entry, path_al_output/202X_FACTURA+PAGAMENT)

            print(f"Processed: {entry.name}")

        except ValueError:
            print(f"WARNING: skipped {entry.name}")

        except Exception as e:
            print(f"WARNING: {e}")


def copy_pdf(origin_path: Path, target_path: Path) -> None:
    # Check to avoid overwriting a file. Shouldn't come up since pdf naming is unique
    dest_file = target_path / origin_path.name if target_path.is_dir() else target_path

    # Changed from using except to raise for Exceptions
    if dest_file.exists():
        raise FileExistsError(f"Destination file already exists: {dest_file}")

    if origin_path.suffix.lower() != ".pdf":
        raise ValueError(f"Origin file {origin_path} is not a PDF file")

    shutil.copy(origin_path, dest_file)

    print(f"Copied: {origin_path}")


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


def change_payment_name(pdf_file: Path, new_payment_name: str) -> None:
    if not pdf_file.exists():
        print(f"WARNING: File not found at {pdf_file}")
        return

    new_path = pdf_file.with_name(f"{new_payment_name}-P.pdf")

    try:
        pdf_file.rename(new_path)
    except FileExistsError:
        print(f"WARNING: A file named {new_path.name} already exists.")


def process_bills_and_payments(
    bills_folder: Path,
    payments_folder: Path,
    merge_folder: Path,
    delete_processed: bool = False,
) -> None:
    merge_folder.mkdir(parents=True, exist_ok=True)

    payment_map = {}
    # Index all payments by their SAP number only
    for payment_path in list_dir(payments_folder):
        if not str(payment_path).endswith(".pdf"):
            log.warning(f"Skipping {payment_path} because it's not a PDF file")
            continue
        payment_numbers = re.sub(r"\D", "", payment_path.stem)
        if not payment_numbers:
            log.warning(
                f"The payment number from this file {payment_path} can't be parsed. Skipping file."
            )
            continue
        payment_map[payment_numbers] = payment_path

    # Check if SAP number matches bills and merge if true
    for bill_path in list_dir(bills_folder):
        bill_numbers = re.sub(r"\D", "", bill_path.stem)
        matched_payment = payment_map.get(bill_numbers)

        if matched_payment:
            output_path = merge_folder / f"{bill_numbers}_F_P.pdf"
            writer = PdfWriter()

            print(f"Merging: {bill_path.name} with {matched_payment.name}...")

            writer.append(bill_path)
            writer.append(matched_payment)

            with open(output_path, "wb") as f:
                writer.write(f)

            if delete_processed:
                bill_path.unlink()
                matched_payment.unlink()
                print(f"Deleted: {output_path}")
        else:
            print(f"WARNING: No matching payment for {bill_path.name}")

    pass
