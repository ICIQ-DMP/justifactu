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

import pypdf
from pypdf import PdfReader

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


def process_bills_and_payments(
    bills_folder: Path,
    payments_folder: Path,
    merge_folder: Path,
    delete_processed: bool = False,
) -> None:
    merge_folder.mkdir(parents=True, exist_ok=True)

    for bill_path in bills_folder.glob("*.pdf"):
        payment_path = payments_folder / bill_path.name

        if payment_path.exists():
            output_path = merge_folder / f"merged_{bill_path.name}"
            writer = pypdf.PdfWriter()

            print(f"Merging: {bill_path.name}...")

            writer.append(bill_path)
            writer.append(payment_path)

            with open(output_path, "wb") as f:
                writer.write(f)

            if delete_processed:
                bill_path.unlink()
                payment_path.unlink()
                print(f"Deleted processed originals for: {bill_path.name}")
        else:
            print(f"Warning: No matching payment found for {bill_path.name}")

    pass
