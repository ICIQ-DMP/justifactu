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

from justifactu.custom_except import SecretCouldNotBeReadFromAnySourceError
from justifactu.secret import read_secret


def test_read_secret_returns_value_from_first_working_source():
    with (
        patch("justifactu.secret.read_file_content", side_effect=FileNotFoundError),
        patch("justifactu.secret.read_env_var", return_value="from-env"),
        patch("justifactu.secret.read_vault_secret") as mock_vault,
    ):
        assert read_secret("SOME_SECRET") == "from-env"

    mock_vault.assert_not_called()


def test_read_secret_logs_per_source_reason_and_raises_when_all_fail():
    with (
        patch(
            "justifactu.secret.read_file_content",
            side_effect=FileNotFoundError("no such file"),
        ),
        patch(
            "justifactu.secret.read_env_var",
            side_effect=KeyError("SOME_SECRET"),
        ),
        patch(
            "justifactu.secret.read_vault_secret",
            side_effect=KeyError("field 'admin_email' not found"),
        ),
        patch("justifactu.secret.log") as mock_log,
        pytest.raises(SecretCouldNotBeReadFromAnySourceError),
    ):
        read_secret("SMTP_ADMIN_EMAIL")

    error_message = mock_log.error.call_args[0][0]
    assert "SMTP_ADMIN_EMAIL" in error_message
    assert "docker secret" in error_message
    assert "local secrets file" in error_message
    assert "environment variable" in error_message
    assert "vault" in error_message
    assert "admin_email" in error_message
    assert mock_log.debug.call_count == 4
