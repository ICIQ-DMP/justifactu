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

import openpyxl
import pdfplumber

from .SAP_ID import SAP_ID
from .custom_except import ParseSAPIdException
from .logger import get_logger

log = get_logger(__name__)

DATE_PATTERN = re.compile(r"^\d{4}$")
AMOUNT_PATTERN = re.compile(r"^\d{1,3}(?:\.\d{3})*,\d{2}$")
CONCEPT_COLUMN_END_X = 289  # next column (location/reference/etc.) starts here
COMMISSION_MARKER = "Comissió per conversió de divises"


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


def _merge_commission_rows(entries: list[BankEntry]) -> list[BankEntry]:
    """Folds a currency-exchange commission row into the immediately
    preceding transaction row (same date) - the ledger records their
    combined total as a single entry, not two."""
    merged: list[BankEntry] = []
    for entry in entries:
        if (
            entry.concept.startswith(COMMISSION_MARKER)
            and merged
            and merged[-1].date == entry.date
        ):
            previous = merged.pop()
            merged.append(
                BankEntry(
                    date=previous.date,
                    concept=previous.concept,
                    total=round(previous.total + entry.total, 2),
                )
            )
        else:
            merged.append(entry)
    return merged


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
    return _merge_commission_rows(entries)


def read_sap_id_ledger(ledger_path: Path) -> dict[tuple[str, float], SAP_ID]:
    """Reads the reconciliation ledger (date/concept/total/SAP ID columns)
    into a (date, total) -> SAP_ID lookup. Rows with no SAP ID in column J
    are skipped."""
    ledger: dict[tuple[str, float], SAP_ID] = {}

    workbook = openpyxl.load_workbook(ledger_path, read_only=True, data_only=True)
    sheet = workbook.active
    if sheet is None:
        raise ValueError(f"No active sheet found in ledger {ledger_path}")

    for row in sheet.iter_rows(min_row=2, values_only=True):
        date_cell, sap_id_cell = row[0], row[9]
        total_cell = row[7]

        if not sap_id_cell:
            continue
        if not isinstance(total_cell, (int, float)):
            log.warning(
                f"Non-numeric total {total_cell!r} in ledger row ({ledger_path.name})",
                extra={"qa_report": True},
            )
            continue
        date = str(date_cell).strip().lstrip("'").replace("/", "")
        total = round(float(total_cell), 2)

        try:
            sap_id = SAP_ID(str(sap_id_cell))
        except ParseSAPIdException:
            log.warning(
                f"Invalid SAP ID {sap_id_cell!r} in ledger row ({ledger_path.name})",
                extra={"qa_report": True},
            )
            continue

        ledger[(date, total)] = sap_id

    workbook.close()
    return ledger


def index_statement_entries(
    pdf_path: Path, ledger_path: Path
) -> dict[SAP_ID, BankEntry]:
    """Matches each bank statement transaction to its SAP ID via the
    reconciliation ledger, keyed by (date, total). Entries with no
    matching ledger row are logged to the QA report and skipped."""
    ledger = read_sap_id_ledger(ledger_path)
    entries_by_sap: dict[SAP_ID, BankEntry] = {}

    for entry in extract_bank_entries(pdf_path):
        key = (entry.date, round(entry.total, 2))
        sap_id = ledger.get(key)

        if sap_id is None:
            log.warning(
                f"No ledger match for statement entry {entry} ({pdf_path.name})",
                extra={"qa_report": True},
            )
            continue

        entries_by_sap[sap_id] = entry

    return entries_by_sap
