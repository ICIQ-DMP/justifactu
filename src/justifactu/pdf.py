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

from pypdf import PdfReader, PdfWriter

from justifactu.filesystem import list_dir
from justifactu.logger import get_logger

log = get_logger(__name__)


def parse_sap_id_from_bill(pdf_path: Path) -> str:
    query_str = r"Fra. \d{10}"
    # restricting the search with the beginning of the year, which appears in the line that
    # we are interested in, which contains the date.
    pattern = re.compile(query_str, re.MULTILINE)

    reader = PdfReader(pdf_path)

    for page_num, page in enumerate(reader.pages):
        # Get text of the page
        text = page.extract_text()
        print("text is: " + text)
        if not text:
            continue

        match = pattern.search(text)
        if not match:
            continue

        return match.group(0).replace("\n", "")

    raise ValueError(f"No SAP ID found in {pdf_path}")


def change_payment_name(pdf_file: Path, new_payment_name: str) -> None:
    if not pdf_file.exists():
        print(f"WARNING: File not found at {pdf_file}")
        return

    new_path = pdf_file.with_name(f"{new_payment_name}.pdf")

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
