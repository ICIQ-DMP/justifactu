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

from justifactu.defines import Mode, Phase
from justifactu.process import run_phase


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
