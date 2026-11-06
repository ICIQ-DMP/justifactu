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

from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Callable

from .SAP_ID import SAP_ID
from .bank_statement import find_year_ledger, index_statement_entries, BankEntry
from .bills import parse_bill_filename
from .custom_except import (
    MergingBillWithPaymentError,
    NotAPaymentFileError,
    ParseSAPIdException,
)

from .defines import FileSuffix, Metric, Phase, Mode
from .paths import (
    bills_folder,
    payments_folder,
    merged_bills_and_payments_folder,
    qa_errors_folder,
    year_merged_folder,
    card_statements_folder,
)
from .filesystem import list_dir, index_folder, change_file_name
from .logger import get_logger
from .payments import index_payments, is_renamed_payment, rename_payment
from .pdf import merge_pdfs

log = get_logger(__name__)

Metrics = Counter[Metric]


def rename_payments(payments_folder: Path) -> Metrics:
    """Phase 1: renames every payment PDF in payments_folder (recursively) to
    {sap_id}-P, in place. Files already renamed by an earlier run are skipped."""
    metrics: Metrics = Counter()
    if not payments_folder.is_dir():
        log.warning(f"{payments_folder} is not a directory")
        return metrics

    for entry in list(payments_folder.rglob("*")):
        if entry.is_dir() or is_renamed_payment(entry):
            continue

        try:
            log.info(f"Renaming: {entry.name}...")
            rename_payment(entry)
        except NotAPaymentFileError as e:
            log.warning(f"Skipping file: {e}", extra={"qa_report": True})
            metrics[Metric.TRASH_FILES] += 1
        except ParseSAPIdException as e:
            log.error(f"Failed to rename {entry}: {e}", extra={"qa_report": True})
            metrics[Metric.UNPARSEABLE_PAYMENTS] += 1
        except FileNotFoundError as e:
            log.error(f"Failed to rename {entry}: {e}", extra={"qa_report": True})

    return metrics


def merge_bills_and_payments(
    bills_folder: Path,
    payments_folder: Path,
    merge_folder: Path,
    delete_processed: bool = False,
    freshly_renamed_payments: dict[SAP_ID, Path] | None = None,
) -> Metrics:
    """Phase 2: merges bills and payments and saves them into merge_folder"""
    metrics: Metrics = Counter()

    merge_folder.mkdir(parents=True, exist_ok=True)
    payment_map = {
        **index_payments(index_folder(payments_folder)),
        **(freshly_renamed_payments or {}),
    }
    qa_folder = qa_errors_folder(merge_folder)
    qa_folder.mkdir(parents=True, exist_ok=True)

    # Process bills and look for matches
    for bill_path in list_dir(bills_folder):
        if not bill_path.is_file() or bill_path.suffix.lower() != ".pdf":
            log.warning(
                f"Skipped bill file because it is not a PDF file: {bill_path}",
                extra={"qa_report": True},
            )
            continue

        try:
            sap = parse_bill_filename(bill_path.stem)
        except ParseSAPIdException:
            log.error(
                f"Failed to merge bill file {bill_path}: unexpected name format.",
                extra={"qa_report": True},
            )
            continue

        matched_payment: Path | None = payment_map.get(sap)

        if not matched_payment:
            log.info(
                f"No direct payment for bill {bill_path}; deferring to card statements"
            )
            continue

        output_folder_path = year_merged_folder(merge_folder, sap.year)
        output_folder_path.mkdir(parents=True, exist_ok=True)

        output_path = (
            output_folder_path / f"{sap}{FileSuffix.MERGED_BILL_PAYMENT.value}.pdf"
        )
        try:
            log.info(f"Merging {bill_path.name} with {matched_payment.name}...")
            merge_pdfs(bill_path, matched_payment, output_path)
        except MergingBillWithPaymentError as e:
            log.error(
                f"Failed to process {bill_path.name}: {e}", extra={"qa_report": True}
            )
            metrics[Metric.FAILED_MERGES] += 1
            continue

        metrics[Metric.PAYMENT_MERGES] += 1
        cleanup_processed_files(bill_path, matched_payment, delete_processed)

    return metrics


def cleanup_processed_files(
    bill_path: Path,
    matched_payment: Path,
    delete_processed: bool,
) -> None:
    """Renames the payment file and optionally deletes the bill file"""
    new_name = f"{matched_payment.stem}{FileSuffix.PROCESSED_PAYMENT.value}"
    try:
        change_file_name(matched_payment, new_name)
        log.info(f"Renamed processed payment file: {matched_payment.name}")

        if delete_processed:
            bill_path.unlink(missing_ok=True)
            log.info(f"Deleted: {bill_path.name}")

    except FileNotFoundError as e:
        log.error(
            f"Failed to rename processed payment file {matched_payment.name}: {e}"
        )


def merge_bills_and_card_statements(
    bills_folder: Path,
    cards_folder: Path,
    merge_folder: Path,
    delete_processed: bool = False,
) -> Metrics:
    """Phase 3: matches remaining bills against card statements through each
    year's ledger, merging the bill with the whole statement. Statements and
    ledgers are never renamed or moved."""
    metrics: Metrics = Counter()

    statement_by_sap: dict[SAP_ID, tuple[Path, BankEntry]] = {}
    if cards_folder.is_dir():
        for year_folder in sorted(p for p in cards_folder.iterdir() if p.is_dir()):
            ledger_path = find_year_ledger(year_folder)
            if ledger_path is None:
                continue
            for statement in sorted(year_folder.glob("*.pdf")):
                entries = index_statement_entries(statement, ledger_path)
                for sap_id, entry in entries.items():
                    statement_by_sap[sap_id] = (statement, entry)
    else:
        log.warning(f"{cards_folder} is not a directory", extra={"qa_report": True})

    for bill_path in list_dir(bills_folder):
        if bill_path.suffix.lower() != ".pdf":
            continue
        try:
            sap = parse_bill_filename(bill_path.stem)
        except ParseSAPIdException:
            continue

        output_folder_path = year_merged_folder(merge_folder, sap.year)
        output_path = (
            output_folder_path / f"{sap}{FileSuffix.MERGED_BILL_PAYMENT.value}.pdf"
        )
        if output_path.exists():
            continue

        match = statement_by_sap.get(sap)
        if match is None:
            log.error(
                f"No matching payment or card statement found for bill {bill_path}",
                extra={"qa_report": True},
            )
            metrics[Metric.UNMATCHED_BILLS] += 1
            continue

        matched_statement, entry = match
        output_folder_path.mkdir(parents=True, exist_ok=True)
        try:
            log.info(
                f"Merging {bill_path.name} with card statement {matched_statement.name}..."
            )
            # Highlights the statement row(s) that pay this bill.
            merge_pdfs(
                bill_path, matched_statement, output_path, highlights=entry.boxes
            )
        except MergingBillWithPaymentError as e:
            log.error(
                f"Failed to process {bill_path.name}: {e}", extra={"qa_report": True}
            )
            metrics[Metric.FAILED_MERGES] += 1
            continue

        metrics[Metric.CARD_STATEMENT_MERGES] += 1
        if delete_processed:
            bill_path.unlink(missing_ok=True)
            log.info(f"Deleted: {bill_path.name}")

    return metrics


def _phase_folders(input_folder: Path) -> tuple[Path, Path, Path]:
    return (
        bills_folder(input_folder),
        payments_folder(input_folder),
        merged_bills_and_payments_folder(input_folder),
    )


def _build_phase_map(
    input_folder: Path, mode: Mode
) -> dict[Phase, Callable[[], Metrics]]:
    bills_folder_path, payments_folder_path, bills_plus_payments_folder = (
        _phase_folders(input_folder)
    )

    def _run_phase_1() -> Metrics:
        return rename_payments(payments_folder_path)

    def _run_phase_2() -> Metrics:
        # Bills are deleted after a successful merge in PROD and TEST, but kept in DEV
        # so local test fixtures survive repeated runs.
        return merge_bills_and_payments(
            bills_folder_path,
            payments_folder_path,
            bills_plus_payments_folder,
            delete_processed=mode != Mode.DEV,
        )

    def _run_phase_3() -> Metrics:
        return merge_bills_and_card_statements(
            bills_folder_path,
            card_statements_folder(input_folder),
            bills_plus_payments_folder,
            delete_processed=mode != Mode.DEV,
        )

    return {
        Phase.PHASE_1: _run_phase_1,
        Phase.PHASE_2: _run_phase_2,
        Phase.PHASE_3: _run_phase_3,
    }


def run_phase(phase: Phase, input_folder: Path, mode: Mode) -> Metrics:
    return _build_phase_map(input_folder, mode)[phase]()


FULL_RUN_PHASES: tuple[Phase, ...] = (Phase.PHASE_1, Phase.PHASE_2, Phase.PHASE_3)


def run_all_phases(input_folder: Path, mode: Mode) -> Metrics:
    phase_map = _build_phase_map(input_folder, mode)
    metrics: Metrics = Counter()
    for phase in FULL_RUN_PHASES:
        metrics.update(phase_map[phase]())
    return metrics


def log_run_summary(metrics: Metrics, elapsed_seconds: float) -> None:
    """Writes the run summary into the QA report. Missing counters read as 0."""
    payment_merges = metrics[Metric.PAYMENT_MERGES]
    card_merges = metrics[Metric.CARD_STATEMENT_MERGES]
    summary = "\n".join(
        [
            "Run summary",
            f"  Execution time: {timedelta(seconds=round(elapsed_seconds))}",
            f"  Bill/payment merges completed: {payment_merges + card_merges} "
            f"({payment_merges} bank payment, {card_merges} card statement)",
            f"  Failed merges: {metrics[Metric.FAILED_MERGES]}",
            f"  Bills with no matching payment: {metrics[Metric.UNMATCHED_BILLS]}",
            f"  Non-payment files in Remeses: {metrics[Metric.TRASH_FILES]}",
            "  Payment files with unparseable SAP ID: "
            f"{metrics[Metric.UNPARSEABLE_PAYMENTS]}",
        ]
    )
    log.info(summary, extra={"qa_report": True})
