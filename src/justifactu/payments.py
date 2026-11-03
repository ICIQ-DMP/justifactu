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

from pypdf import PdfReader
from pypdf.errors import DependencyError, PyPdfError

from .SAP_ID import SAP_ID, parse_sap_id_from_string
from .SAP_ID import pattern as SAP_pattern
from .custom_except import NotAPaymentFileError, ParseSAPIdException
from .defines import FileSuffix
from .filesystem import change_file_name
from .logger import get_logger

log = get_logger(__name__)

# Matches payments already handled by an earlier run: {sap_id}-P or {sap_id}-P_merged
RENAMED_PAYMENT_PATTERN = re.compile(
    SAP_pattern + r"-P(" + re.escape(FileSuffix.PROCESSED_PAYMENT.value) + r")?$"
)


def index_payments(folder_map: dict[str, Path]) -> dict[SAP_ID, Path]:
    payment_map: dict[SAP_ID, Path] = {}

    for filename, payment_path in folder_map.items():

        if payment_path.stem.endswith(FileSuffix.PROCESSED_PAYMENT.value):
            log.info(f"Skipping {payment_path} because it is already processed")
            continue

        try:
            sap_number = parse_sap_id_from_string(filename)
            payment_map[sap_number] = payment_path

        except ParseSAPIdException:
            log.error(f"Failed to parse SAP ID from {payment_path}: {filename}")

    return payment_map


def is_renamed_payment(path: Path) -> bool:
    """Whether a payment file was already renamed by an earlier run."""
    return RENAMED_PAYMENT_PATTERN.search(path.stem) is not None


def rename_payment(payment_path: Path) -> Path:
    """Renames one payment file to {sap_id}-P in place, returning the new path.

    Raises NotAPaymentFileError for non-PDF files, and ParseSAPIdException
    when no SAP ID can be read from the PDF."""
    if payment_path.suffix.lower() != ".pdf":
        raise NotAPaymentFileError(f"{payment_path} is not a PDF file")

    sap_id = parse_sap_id_from_payment(payment_path)
    return change_file_name(payment_path, f"{sap_id}-P")


def parse_sap_id_from_payment(pdf_path: Path) -> str:
    """Reads a PDF file to extract the SAP id"""
    query_str = r"(Fra\.?\s+)" + SAP_pattern

    pattern = re.compile(query_str, re.MULTILINE | re.IGNORECASE)

    try:
        reader = PdfReader(pdf_path)

        for page in reader.pages:
            text = page.extract_text()
            if not text:
                continue

            match = pattern.search(text)

            if not match:
                continue

            return match.group("year") + match.group("sapid")
    except (PyPdfError, DependencyError) as e:
        raise ParseSAPIdException(f"Could not read {pdf_path}: {e}") from e

    raise ParseSAPIdException(f"No SAP ID found in {pdf_path}")
