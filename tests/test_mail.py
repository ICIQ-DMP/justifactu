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

from datetime import datetime
from unittest.mock import patch, MagicMock

from justifactu.defines import SecretNames
from justifactu.mail import (
    send_mail,
    build_result_mail_body,
    build_admin_error_mail_body,
    send_mail_authenticated,
    mail_process,
)

from justifactu.secret import read_secret

# ── send_mail ─────────────────────────────────────────────────────────────────


@patch("justifactu.mail.smtplib.SMTP")
@patch("justifactu.mail.MIMEMultipart")
@patch("justifactu.mail.MIMEText")
def test_send_mail(mock_mime_text, mock_multipart, mock_smtp):
    mock_msg_instance = MagicMock()
    mock_msg_instance.as_string.return_value = "Mocked Email String"
    mock_multipart.return_value = mock_msg_instance

    mock_smtp_instance = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

    send_mail(
        to_email="user@example.com",
        subject="Test Subject",
        body="Test Body",
        from_email="admin@example.com",
        username="smtp_user",
        password="smtp_password",
        server="smtp.office365.com",
        port=587,
    )

    mock_mime_text.assert_called_once_with("Test Body")
    mock_msg_instance.__setitem__.assert_any_call("Subject", "Test Subject")
    mock_msg_instance.__setitem__.assert_any_call("From", "admin@example.com")
    mock_msg_instance.__setitem__.assert_any_call("To", "user@example.com")
    mock_msg_instance.attach.assert_called_once_with(mock_mime_text.return_value)

    mock_smtp.assert_called_once_with("smtp.office365.com", 587)
    mock_smtp_instance.ehlo.assert_called_once()
    mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_once_with("smtp_user", "smtp_password")
    mock_smtp_instance.sendmail.assert_called_once_with(
        "admin@example.com", ["user@example.com"], "Mocked Email String"
    )


# ── build_result_mail_body ────────────────────────────────────────────────────


@patch("justifactu.mail.unparse_date")
def test_build_result_mail_body(mock_unparse_date):
    mock_unparse_date.side_effect = ["01/01/2026", "31/01/2026"]

    result = build_result_mail_body(
        result_link="https://sharepoint.com/results",
        log_link="https://sharepoint.com/logs",
        title="Justification Request Q1",
        request="REQ-123",
        name="Jane Doe",
        begin=datetime(2026, 1, 1),
        end=datetime(2026, 1, 31),
        owner_email="owner@example.com",
    )

    assert "Justification Request Q1" in result
    assert "REQ-123" in result
    assert "Jane Doe" in result
    assert "01/01/2026" in result
    assert "31/01/2026" in result
    assert "https://sharepoint.com/results" in result
    assert "https://sharepoint.com/logs" in result
    assert "owner@example.com" in result
    assert mock_unparse_date.call_count == 2


# ── build_admin_error_mail_body ───────────────────────────────────────────────


def test_build_admin_error_mail_body():
    result = build_admin_error_mail_body(request="REQ-999")

    assert "REQ-999" in result
    assert "ha fallat estrepitosament" in result
    assert "workflow (Jenkins)" in result


# ── send_mail_authenticated ───────────────────────────────────────────────────


@patch("justifactu.mail.send_mail")
@patch("justifactu.mail.read_secret")
@patch("justifactu.mail.log")
def test_send_mail_authenticated(mock_log, mock_read_secret, mock_send_mail):
    mock_read_secret.side_effect = ["my_user", "my_pass", "smtp.test.com", "587"]

    send_mail_authenticated(
        to_email="target@example.com", subject="Auth Subject", body="Auth Body"
    )

    assert mock_read_secret.call_count == 4

    mock_send_mail.assert_called_once_with(
        to_email="target@example.com",
        subject="Auth Subject",
        body="Auth Body",
        from_email="my_user",
        username="my_user",
        password="my_pass",
        server="smtp.test.com",
        port=587,
        attachment_paths=None,
    )


# ── mail_process ──────────────────────────────────────────────────────────────


@patch("justifactu.mail.send_mail_authenticated")
@patch("justifactu.mail.build_result_mail_body")
@patch("justifactu.mail.log")
def test_mail_process(mock_log, mock_build_body, mock_send_auth):
    mock_build_body.return_value = "Mocked Final Body"

    begin_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 1, 31)

    mail_process(
        result_link="link_to_res",
        log_link="link_to_log",
        title="Title X",
        request="REQ-10",
        name="John",
        author="author@example.com",
        begin=begin_date,
        end=end_date,
        owner_email="owner@example.com",
    )

    mock_build_body.assert_called_once_with(
        result_link="link_to_res",
        log_link="link_to_log",
        title="Title X",
        request="REQ-10",
        name="John",
        begin=begin_date,
        end=end_date,
        owner_email="owner@example.com",
    )

    expected_subject = (
        'Justifactu - La petició "Title X" amb ID REQ-10 ha estat completada amb èxit'
    )
    mock_send_auth.assert_called_once_with(
        "author@example.com", expected_subject, "Mocked Final Body"
    )

    mock_log.info.assert_called_once_with("Email sent. Process complete.")


def test_send_mail_authenticated_real():
    print(read_secret(SecretNames.SMTP_SERVER.value))
    print(read_secret(SecretNames.SMTP_PORT.value))

    # send_mail_authenticated(
    #     read_secret(SecretNames.SMTP_DEVELOPER_EMAIL.value),
    #     "Prova mailing",
    #     "Cos de la prova de mailing",
    # )
