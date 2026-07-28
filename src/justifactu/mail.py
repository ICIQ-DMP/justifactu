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

"""Email delivery utilities for notifying users about completed justifications."""

import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from .date import unparse_date
from .defines import SecretNames
from .logger import get_logger
from .secret import read_secret

log = get_logger(__name__)


def send_mail(
    to_email: str,
    subject: str,
    body: str,
    from_email: str,
    username: str,
    password: str,
    server: str,
    port: int,
    attachment_paths: list[Path] | None = None,
) -> dict[str, tuple[int, bytes]]:
    """Send a plain-text email via SMTP with STARTTLS, optionally with file attachments."""
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.attach(MIMEText(body))

    for attachment_path in attachment_paths or []:
        attachment = MIMEApplication(
            attachment_path.read_bytes(), Name=attachment_path.name
        )
        attachment["Content-Disposition"] = (
            f'attachment; filename="{attachment_path.name}"'
        )
        msg.attach(attachment)

    with smtplib.SMTP(server, port) as socket:
        socket.ehlo()
        socket.starttls()
        socket.login(username, password)
        return socket.sendmail(from_email, [to_email], msg.as_string())


def build_result_mail_body(
    result_link: str,
    log_link: str,
    title: str,
    request: str,
    name: str,
    begin: datetime,
    end: datetime,
    owner_email: str,
) -> str:
    """Builds the body of the email to send to the user."""
    return (
        f"Hola!\n"
        f"\n"
        f'T\'informo que la petició que vas fer al Justifactu amb títol "{title}" i ID {request} per'
        f' a l\'empleat amb nom "{name}" des del {unparse_date(begin)} fins al {unparse_date(end)} '
        f"ja ha sigut resolta.\n"
        f"\n"
        f"Et deixo aquí els resultats:\n"
        f"\n"
        f"* Carpeta Sharepoint amb els documents (inclou resum a l'arrel de la carpeta): {result_link}.\n"
        f"* Fitxer de logs (només administradors): {log_link}.\n"
        f"\n"
        f"Per a qualsevol dubte o problema contacteu al Product Owner del Justicier, a"
        f" {owner_email}.\n"
        f"\n"
        f"Seguim,\n"
        f"\n"
        f"\n"
        f"David (Avatar Digital)\n"
        f"\n"
        f"Aquest missatge ha estat auto-generat."
    )


def build_admin_error_mail_body(
    request: str,
) -> str:
    """Builds the body of the email to send to the user."""
    return (
        f"Hola!\n"
        f"\n"
        f"T'informo que la petició que vas fer al Justifactu amb ID {request} ha fallat estrepitosament a nivell de "
        f"workflow (Jenkins). Probablement l'error està a la infrastructura i no al codi. Revisa el servidor, els "
        f"Dockers i el Jenkinsfile ja que és a on probablement estarà l'error."
        f"\n"
        f"Seguim,\n"
        f"\n"
        f"\n"
        f"David (Avatar Digital)\n"
        f"\n"
        f"Aquest missatge ha estat auto-generat."
    )


def send_mail_authenticated(
    to_email: str,
    subject: str,
    body: str,
    attachment_paths: list[Path] | None = None,
) -> dict[str, tuple[int, bytes]]:
    """Send a plain-text email via SMTP with STARTTLS with authentication handled."""
    smtp_user = read_secret(SecretNames.SMTP_USERNAME.value)
    smtp_password = read_secret(SecretNames.SMTP_PASSWORD.value)
    smtp_host = read_secret(SecretNames.SMTP_SERVER.value)
    smtp_port = int(read_secret(SecretNames.SMTP_PORT.value))

    return send_mail(
        to_email=to_email,
        subject=subject,
        body=body,
        from_email=smtp_user,
        username=smtp_user,
        password=smtp_password,
        server=smtp_host,
        port=smtp_port,
        attachment_paths=attachment_paths,
    )


def mail_process(
    result_link: str,
    log_link: str,
    title: str,
    request: str,
    name: str,
    author: str,
    begin: datetime,
    end: datetime,
    owner_email: str,
) -> None:
    """Read SMTP credentials and send the completion notification email.

    Args:
        result_link: SharePoint URL to the result folder.
        log_link: SharePoint URL to the log file.
        title: Title of the request.
        request: ID of the request from Sharepoint List.
        name: Name of the person that is being justified.
        author: Author of the justification request.
        begin: Date of the beginning of the justification request.
        end: Date of the end of the justification request.
        owner_email: Email of the person who owns Justicier.
    """
    subject = f'Justifactu - La petició "{title}" amb ID {request} ha estat completada amb èxit'
    body = build_result_mail_body(
        result_link=result_link,
        log_link=log_link,
        title=title,
        request=request,
        name=name,
        begin=begin,
        end=end,
        owner_email=owner_email,
    )

    send_mail_authenticated(author, subject, body)

    log.info("Email sent. Process complete.")


def send_qa_report_mail(
    to_email: str,
    message: str,
    qa_report_path: Path,
    additional_attachments: list[Path] | None = None,
) -> None:
    """Send the run's QA report and log file(s) as attachments, with a custom message.

    Args:
        to_email: Recipient email address.
        message: Free-text message making up the email body.
        qa_report_path: Path to the QA report log file generated during the run.
        additional_attachments: Any further files to attach (e.g. the full run log).
    """
    subject = f"Justifactu - QA report {qa_report_path.stem}"
    send_mail_authenticated(
        to_email,
        subject,
        message,
        attachment_paths=[qa_report_path, *(additional_attachments or [])],
    )
    log.info("QA report email sent.")
