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
from .SAP_ID import pattern as SAP_pattern

from .SAP_ID import SAP_ID
from .custom_except import (
    ParseSAPIdException,
)
from .logger import get_logger

log = get_logger(__name__)


def parse_bill_filename(bill_name: str) -> SAP_ID:
    bill_patt = re.compile(rf"F\s{SAP_pattern}")

    match = bill_patt.fullmatch(bill_name)

    if not match:
        raise ParseSAPIdException(f"Failed to parse {bill_name}")

    bill_sap_id = SAP_ID(match.group("year") + match.group("sapid"))

    return bill_sap_id


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
