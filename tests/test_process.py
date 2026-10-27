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
from unittest.mock import patch

import pytest

from justifactu.SAP_ID import SAP_ID
from justifactu.defines import Mode, Phase
from justifactu.process import run_phase, run_all_phases


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
        run_phase(Phase.PHASE_2, tmp_path, mode, tmp_path / "ledger.xlsx")

    assert mock_merge.call_args.kwargs["delete_processed"] is expected_delete_processed


def test_run_all_phases_passes_phase_1_result_into_phase_2(tmp_path):
    ledger_path = tmp_path / "ledger.xlsx"
    sap_id_a = SAP_ID("2034567890")
    statement_path = tmp_path / "statement.pdf"

    with (
        patch(
            "justifactu.process.rename_payments",
            return_value={sap_id_a: statement_path},
        ),
        patch("justifactu.process.merge_bills_and_payments") as mock_merge,
    ):
        run_all_phases(tmp_path, Mode.TEST, ledger_path)

    assert mock_merge.call_args.kwargs["freshly_renamed_payments"] == {
        sap_id_a: statement_path
    }
