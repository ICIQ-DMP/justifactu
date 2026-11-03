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
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from conftest import create_blank_pdf
from justifactu.SAP_ID import SAP_ID
from justifactu.defines import FileSuffix, Mode, Phase, Metric
from justifactu.paths import (
    bills_folder,
    card_statements_folder,
    merged_bills_and_payments_folder,
    year_merged_folder,
)
from justifactu.logger import configure_logging_from_settings
from justifactu.process import (
    FULL_RUN_PHASES,
    log_run_summary,
    merge_bills_and_card_statements,
    run_all_phases,
    run_phase,
)


@pytest.mark.parametrize(
    "mode, expected_delete_processed",
    [
        (Mode.PROD, True),
        (Mode.TEST, True),
        (Mode.DEV, False),
    ],
)
def test_run_phase_2_delete_processed_depends_on_mode(
    tmp_path, mode, expected_delete_processed
):
    with patch("justifactu.process.merge_bills_and_payments") as mock_merge:
        run_phase(Phase.PHASE_2, tmp_path, mode)

    assert mock_merge.call_args.kwargs["delete_processed"] is expected_delete_processed


# ── merge_bills_and_card_statements (phase 3) ────────────────────────────────

CARD_SAP_ID = SAP_ID("2026000123")


def _card_layout(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """FACTURES/ plus Targetes/2026/ with one ledger and one statement."""
    bills_dir = bills_folder(tmp_path)
    bills_dir.mkdir()
    year_dir = card_statements_folder(tmp_path) / "2026"
    year_dir.mkdir(parents=True)
    (year_dir / "Targetes_2026.xlsx").touch()
    statement = year_dir / "tarja.pdf"
    create_blank_pdf(statement)
    return bills_dir, year_dir, statement, merged_bills_and_payments_folder(tmp_path)


def _expected_output(merge_dir: Path, sap: SAP_ID) -> Path:
    return (
        year_merged_folder(merge_dir, sap.year)
        / f"{sap}{FileSuffix.MERGED_BILL_PAYMENT.value}.pdf"
    )


def test_phase_3_merges_bill_with_matching_card_statement(tmp_path):
    bills_dir, _, statement, merge_dir = _card_layout(tmp_path)
    bill = bills_dir / f"F {CARD_SAP_ID}.pdf"
    create_blank_pdf(bill)

    with patch(
        "justifactu.process.index_statement_entries",
        return_value={CARD_SAP_ID: MagicMock()},
    ):
        merge_bills_and_card_statements(
            bills_dir,
            card_statements_folder(tmp_path),
            merge_dir,
            delete_processed=True,
        )

    assert _expected_output(merge_dir, CARD_SAP_ID).exists()
    assert not bill.exists()
    assert statement.exists()  # statements are never renamed or moved


def test_phase_3_keeps_bill_when_delete_processed_false(tmp_path):
    bills_dir, _, _, merge_dir = _card_layout(tmp_path)
    bill = bills_dir / f"F {CARD_SAP_ID}.pdf"
    create_blank_pdf(bill)

    with patch(
        "justifactu.process.index_statement_entries",
        return_value={CARD_SAP_ID: MagicMock()},
    ):
        merge_bills_and_card_statements(
            bills_dir,
            card_statements_folder(tmp_path),
            merge_dir,
            delete_processed=False,
        )

    assert _expected_output(merge_dir, CARD_SAP_ID).exists()
    assert bill.exists()


def test_phase_3_skips_bill_already_merged(tmp_path):
    bills_dir, _, _, merge_dir = _card_layout(tmp_path)
    create_blank_pdf(bills_dir / f"F {CARD_SAP_ID}.pdf")
    existing = _expected_output(merge_dir, CARD_SAP_ID)
    existing.parent.mkdir(parents=True)
    existing.touch()

    with (
        patch(
            "justifactu.process.index_statement_entries",
            return_value={CARD_SAP_ID: MagicMock()},
        ),
        patch("justifactu.process.merge_pdfs") as mock_merge,
    ):
        merge_bills_and_card_statements(
            bills_dir,
            card_statements_folder(tmp_path),
            merge_dir,
            delete_processed=True,
        )

    mock_merge.assert_not_called()


def test_phase_3_qa_logs_bill_with_no_match(tmp_path, caplog):
    bills_dir, _, _, merge_dir = _card_layout(tmp_path)
    create_blank_pdf(bills_dir / f"F {CARD_SAP_ID}.pdf")

    with patch("justifactu.process.index_statement_entries", return_value={}):
        merge_bills_and_card_statements(
            bills_dir,
            card_statements_folder(tmp_path),
            merge_dir,
            delete_processed=True,
        )

    records = [
        r
        for r in caplog.records
        if "No matching payment or card statement" in r.getMessage()
    ]
    assert len(records) == 1
    assert records[0].qa_report is True
    assert not _expected_output(merge_dir, CARD_SAP_ID).exists()


def test_phase_3_qa_logs_unmatched_bill_when_targetes_missing(tmp_path, caplog):
    bills_dir = bills_folder(tmp_path)
    bills_dir.mkdir()
    create_blank_pdf(bills_dir / f"F {CARD_SAP_ID}.pdf")

    merge_bills_and_card_statements(
        bills_dir,
        card_statements_folder(tmp_path),  # never created
        merged_bills_and_payments_folder(tmp_path),
        delete_processed=True,
    )

    assert any(
        "No matching payment or card statement" in r.getMessage()
        for r in caplog.records
    )


def test_phase_3_skips_year_folder_without_ledger(tmp_path):
    bills_dir, year_dir, _, merge_dir = _card_layout(tmp_path)
    (year_dir / "Targetes_2026.xlsx").unlink()

    with patch("justifactu.process.index_statement_entries") as mock_index:
        merge_bills_and_card_statements(
            bills_dir,
            card_statements_folder(tmp_path),
            merge_dir,
            delete_processed=True,
        )

    mock_index.assert_not_called()


# ── phase 3 wiring ───────────────────────────────────────────────────────────


def test_full_run_includes_phase_3():
    assert FULL_RUN_PHASES == (Phase.PHASE_1, Phase.PHASE_2, Phase.PHASE_3)


@pytest.mark.parametrize(
    "mode, expected_delete_processed",
    [
        (Mode.PROD, True),
        (Mode.TEST, True),
        (Mode.DEV, False),
    ],
)
def test_run_phase_3_delete_processed_depends_on_mode(
    tmp_path, mode, expected_delete_processed
):
    with patch("justifactu.process.merge_bills_and_card_statements") as mock_merge:
        run_phase(Phase.PHASE_3, tmp_path, mode)

    assert mock_merge.call_args.kwargs["delete_processed"] is expected_delete_processed


# ── run metrics ──────────────────────────────────────────────────────────────


def test_phase_3_counts_merges_and_unmatched_bills(tmp_path):
    bills_dir, _, _, merge_dir = _card_layout(tmp_path)
    create_blank_pdf(bills_dir / f"F {CARD_SAP_ID}.pdf")
    create_blank_pdf(bills_dir / "F 2026000999.pdf")  # not in any statement

    with patch(
        "justifactu.process.index_statement_entries",
        return_value={CARD_SAP_ID: MagicMock()},
    ):
        metrics = merge_bills_and_card_statements(
            bills_dir,
            card_statements_folder(tmp_path),
            merge_dir,
            delete_processed=True,
        )

    assert metrics[Metric.CARD_STATEMENT_MERGES] == 1
    assert metrics[Metric.UNMATCHED_BILLS] == 1


def test_phase_3_counts_failed_merge_and_keeps_bill(tmp_path):
    bills_dir, _, statement, merge_dir = _card_layout(tmp_path)
    bill = bills_dir / f"F {CARD_SAP_ID}.pdf"
    create_blank_pdf(bill)
    statement.write_bytes(b"not a pdf")

    with patch(
        "justifactu.process.index_statement_entries",
        return_value={CARD_SAP_ID: MagicMock()},
    ):
        metrics = merge_bills_and_card_statements(
            bills_dir,
            card_statements_folder(tmp_path),
            merge_dir,
            delete_processed=True,
        )

    assert metrics[Metric.FAILED_MERGES] == 1
    assert bill.exists()
    assert not _expected_output(merge_dir, CARD_SAP_ID).exists()


def test_run_all_phases_adds_up_every_phase(tmp_path):
    with (
        patch(
            "justifactu.process.rename_payments",
            return_value=Counter({Metric.TRASH_FILES: 2}),
        ),
        patch(
            "justifactu.process.merge_bills_and_payments",
            return_value=Counter({Metric.PAYMENT_MERGES: 3}),
        ),
        patch(
            "justifactu.process.merge_bills_and_card_statements",
            return_value=Counter(
                {Metric.CARD_STATEMENT_MERGES: 1, Metric.UNMATCHED_BILLS: 4}
            ),
        ),
    ):
        metrics = run_all_phases(tmp_path, Mode.TEST)

    assert metrics == Counter(
        {
            Metric.TRASH_FILES: 2,
            Metric.PAYMENT_MERGES: 3,
            Metric.CARD_STATEMENT_MERGES: 1,
            Metric.UNMATCHED_BILLS: 4,
        }
    )


def test_log_run_summary_is_written_to_qa_report(tmp_path):
    qa_report_path = tmp_path / "qa_report.log"
    configure_logging_from_settings(qa_files_log_file=qa_report_path)
    metrics = Counter(
        {
            Metric.PAYMENT_MERGES: 3,
            Metric.CARD_STATEMENT_MERGES: 2,
            Metric.UNMATCHED_BILLS: 4,
            Metric.TRASH_FILES: 1,
            Metric.UNPARSEABLE_PAYMENTS: 6,
        }
    )

    log_run_summary(metrics, elapsed_seconds=3725.4)

    content = qa_report_path.read_text()
    assert "Execution time: 1:02:05" in content
    assert (
        "Bill/payment merges completed: 5 (3 bank payment, 2 card statement)" in content
    )
    assert "Failed merges: 0" in content  # missing counters read as 0
    assert "Bills with no matching payment: 4" in content
    assert "Non-payment files in Remeses: 1" in content
    assert "Payment files with unparseable SAP ID: 6" in content
