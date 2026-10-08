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
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from justifactu.notify import main, parse_arguments

# ── parse_arguments ───────────────────────────────────────────────────────────


def test_parse_arguments_requires_subject_and_body(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--to", "a@b.com"])
    with pytest.raises(SystemExit):
        parse_arguments()


def test_parse_arguments_to_defaults_to_none(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--subject", "s", "--body", "b"])
    args = parse_arguments()
    assert args.to is None


def test_parse_arguments_attach_is_repeatable_and_becomes_paths(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--subject",
            "s",
            "--body",
            "b",
            "--attach",
            "a.log",
            "--attach",
            "b.log",
        ],
    )
    args = parse_arguments()
    assert args.attachments == [Path("a.log"), Path("b.log")]


def test_parse_arguments_attach_defaults_to_none(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--subject", "s", "--body", "b"])
    args = parse_arguments()
    assert args.attachments is None


# ── main ──────────────────────────────────────────────────────────────────────


def test_main_uses_explicit_to_when_given(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--to", "a@b.com", "--subject", "s", "--body", "b"],
    )
    with (
        patch("justifactu.notify.send_mail_authenticated") as mock_send,
        patch("justifactu.notify.read_secret") as mock_secret,
    ):
        main()

    mock_send.assert_called_once_with(
        to_email="a@b.com", subject="s", body="b", attachment_paths=None
    )
    mock_secret.assert_not_called()


def test_main_falls_back_to_admin_email_secret_when_to_omitted(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--subject", "s", "--body", "b"])

    with (
        patch("justifactu.notify.send_mail_authenticated") as mock_send,
        patch(
            "justifactu.notify.read_secret", return_value="admin@example.com"
        ) as mock_secret,
    ):
        main()

    mock_secret.assert_called_once_with("SMTP_ADMIN_EMAIL")
    mock_send.assert_called_once_with(
        to_email="admin@example.com", subject="s", body="b", attachment_paths=None
    )


def test_main_passes_attachments_through(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--to",
            "a@b.com",
            "--subject",
            "s",
            "--body",
            "b",
            "--attach",
            "run.log",
        ],
    )
    with patch("justifactu.notify.send_mail_authenticated") as mock_send:
        main()

    mock_send.assert_called_once_with(
        to_email="a@b.com", subject="s", body="b", attachment_paths=[Path("run.log")]
    )


def test_main_lets_send_failure_propagate(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--to", "a@b.com", "--subject", "s", "--body", "b"],
    )
    with patch(
        "justifactu.notify.send_mail_authenticated",
        side_effect=RuntimeError("smtp down"),
    ):
        with pytest.raises(RuntimeError, match="smtp down"):
            main()
