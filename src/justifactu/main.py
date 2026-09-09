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

from justifactu.arguments import process_parse_arguments
from justifactu.defines import NOW, FolderName, SecretNames
from justifactu.logger import (
    ADMIN_LOG_FOLDER,
    configure_logging_from_settings,
    get_logger,
    get_user_log_path,
)
from justifactu.filesystem import copy_file
from justifactu.mail import send_qa_report_mail
from justifactu.process import run_all_phases
from justifactu.custom_except import MainCriticalError
from justifactu.secret import read_secret

log = get_logger(__name__)


def main() -> None:
    """"""
    qa_report_path = ADMIN_LOG_FOLDER / (NOW + "_qa_report.log")
    configure_logging_from_settings(qa_files_log_file=qa_report_path)

    args = process_parse_arguments()
    input_folder = args.input_location

    log.info("Starting...")

    try:
        run_all_phases(input_folder)

        bills_plus_payments_folder = (
            input_folder.parent
            / FolderName.OUTPUT.value
            / FolderName.MERGED_OUTPUT.value
        )
        qa_folder = bills_plus_payments_folder / FolderName.QA_ERRORS.value
        copy_file(qa_report_path, qa_folder)
        regular_log_path = ADMIN_LOG_FOLDER / (NOW + ".log")
        copy_file(regular_log_path, qa_folder)

        log.info("Finished...")

    except MainCriticalError as e:
        log.critical(e)

    finally:
        try:
            send_qa_report_mail(
                to_email=read_secret(SecretNames.SMTP_DEVELOPER_EMAIL.value),
                message="Adjuntem el informe QA de l'execució.",
                qa_report_path=qa_report_path,
                additional_attachments=[get_user_log_path()],
            )
        except Exception as e:
            log.error(f"Failed to send QA report email: {e}")
