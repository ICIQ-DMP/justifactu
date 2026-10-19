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
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

import pdfplumber

from .SAP_ID import SAP_ID, parse_sap_id_from_string
from .custom_except import ParseSAPIdException
from .logger import get_logger

log = get_logger(__name__)

DATE_PATTERN = re.compile(r"^\d{4}$")
AMOUNT_PATTERN = re.compile(r"^\d{1,3}(?:\.\d{3})*,\d{2}$")
CONCEPT_COLUMN_END_X = 289  # next column (location/reference/etc.) starts here


class Word(TypedDict):
    """The subset of pdfplumber's extract_words() fields this module reads."""

    text: str
    x0: float
    top: float


@dataclass
class BankEntry:
    date: str  # DDMM
    concept: str
    total: float


def _group_into_rows(words: list[Word], tolerance: float = 1.0) -> list[list[Word]]:
    """Groups words sharing (approximately) the same 'top' into rows,
    each row's words sorted left to right."""
    rows: list[list[Word]] = []
    for word in sorted(words, key=lambda w: w["top"]):
        for row in rows:
            if abs(row[0]["top"] - word["top"]) <= tolerance:
                row.append(word)
                break
        else:
            rows.append([word])
    for row in rows:
        row.sort(key=lambda w: w["x0"])
    return rows


def _parse_amount(text: str) -> float:
    return float(text.replace(".", "").replace(",", "."))


def extract_bank_entries(pdf_path: Path) -> list[BankEntry]:
    """Parses every transaction row out of a bank statement PDF."""
    entries: list[BankEntry] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # pdfplumber's own return type is an untyped dict shape; Word
            # documents the fields this module actually relies on.
            words = cast(list[Word], page.extract_words())
            for row in _group_into_rows(words):
                if not row or not DATE_PATTERN.match(row[0]["text"]):
                    continue  # not a transaction row (header/footer/summary line)

                date = row[0]["text"]
                concept = " ".join(
                    w["text"] for w in row[1:] if w["x0"] < CONCEPT_COLUMN_END_X
                )

                amount_words = [
                    w["text"] for w in row if AMOUNT_PATTERN.match(w["text"])
                ]
                if not amount_words:
                    log.warning(
                        f"Skipping malformed statement row (no amount found): "
                        f"{date} {concept!r} in {pdf_path.name}",
                        extra={"qa_report": True},
                    )
                    continue
                total = _parse_amount(amount_words[-1])

                entries.append(BankEntry(date=date, concept=concept, total=total))
    return entries


def index_statement_entries(pdf_path: Path) -> dict[SAP_ID, BankEntry]:
    """Maps each SAP ID found in a bank statement's transaction concepts
    to the entry it was found in. Entries whose concept carries no SAP ID
    are logged to the QA report and skipped."""
    entries_by_sap: dict[SAP_ID, BankEntry] = {}

    for entry in extract_bank_entries(pdf_path):
        try:
            sap_id = parse_sap_id_from_string(entry.concept)
        except ParseSAPIdException:
            log.warning(
                f"No SAP ID in statement concept {entry.concept!r} ({pdf_path.name})",
                extra={"qa_report": True},
            )
            continue

        entries_by_sap[sap_id] = entry

    return entries_by_sap
