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

from .custom_except import (
    ParseSAPIdException,
    SkippedPdfRenamingInvalidSapId,
    UnexpectedRenamingError,
)
from .SAP_ID import pattern as SAP_pattern
from .filesystem import change_file_name
from .logger import get_logger

log = get_logger(__name__)


def parse_sap_id_from_bill(pdf_path: Path) -> str:
    """Reads a PDF file to extract the SAP id"""
    query_str = r"(Fra\.?\s+)" + SAP_pattern

    pattern = re.compile(query_str, re.MULTILINE)

    reader = PdfReader(pdf_path)

    for page in reader.pages:
        text = page.extract_text()
        if not text:
            continue

        match = pattern.search(text)

        if not match:
            continue

        return match.group("year") + match.group("sapid")

    raise ParseSAPIdException(f"No SAP ID found in {pdf_path}")


def merge_pdfs(first_pdf: Path, second_pdf: Path, output_path: Path) -> None:
    """Merges two PDF files into output_path"""
    writer = PdfWriter()
    writer.append(first_pdf)
    writer.append(second_pdf)

    with open(output_path, "wb") as f:
        writer.write(f)
        writer.close()


def rename_payments(pdf_path: Path) -> None:
    """Renames the files from the payments folder"""
    if not pdf_path.is_dir():
        log.warning(f"{pdf_path} is not a directory")

    rename_pattern = re.compile(SAP_pattern + r"-P$")

    for entry in list(pdf_path.rglob("*")):
        if entry.is_dir():
            continue

        if rename_pattern.search(entry.stem):
            continue

        if entry.suffix.lower() != ".pdf":
            log.warning(f"Skipping file {entry}: non-PDF file")
            continue

        try:
            log.info(f"Renaming: {entry.name}...")

            sap_id = parse_sap_id_from_bill(entry)

            updated_entry = change_file_name(entry, f"{sap_id}-P")

            if not updated_entry:
                continue

            log.info(f"File name changed to: {updated_entry.name}")

        except ParseSAPIdException as e:
            log.error(f"Failed to parse SAP ID from {entry}: {e}")

        except SkippedPdfRenamingInvalidSapId:
            log.warning(f"Skipped {entry.name} due to invalid value")

        except UnexpectedRenamingError as e:
            log.exception(f"Unexpected error processing {entry.name}: {e}")
