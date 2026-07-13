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
from pathlib import Path

from justifactu.arguments import process_parse_arguments
from justifactu.defines import NOW, InputLocation, FolderName, ROOT_FOLDER, SecretNames
from justifactu.logger import (
    ADMIN_LOG_FOLDER,
    configure_logging_from_settings,
    get_logger,
)
from justifactu.filesystem import copy_file
from justifactu.mail import send_qa_report_mail
from justifactu.process import merge_bills_and_payments
from justifactu.pdf import rename_payments
from justifactu.custom_except import MainCriticalError
from justifactu.secret import read_secret
from justifactu.sharepoint import (
    _connect_sharepoint,
    build_file_url_map,
    # download_input_folder,
    upload_folder_recursive,
)

logger = get_logger(__name__)


def main() -> None:
    """"""
    qa_report_path = ADMIN_LOG_FOLDER / (NOW + "_qa_report.log")
    configure_logging_from_settings(
        moved_files_log_file=qa_report_path,
    )

    args = process_parse_arguments()
    args.location = InputLocation.SHAREPOINT

    default_input_folder = ROOT_FOLDER / "service/onedrive/data/justifactu/_input"

    token_manager = None
    site_id = None
    drive_id = None

    # TODO comentar implementació amb Aleix
    if args.location == InputLocation.LOCAL:
        input_folder = args.input_location or default_input_folder
    else:
        input_folder = default_input_folder
        token_manager, site_id, drive_id = _connect_sharepoint()
        # download_input_folder(
        #    token_manager,
        #    drive_id,
        #    Path(FolderName.SHAREPOINT_INPUT_PATH),
        #    input_folder,
        # )
    bills_folder = input_folder / FolderName.BILLS_INPUT.value
    payments_folder = input_folder / FolderName.PAYMENTS_INPUT.value
    bills_plus_payments_folder = (
        input_folder.parent / "_output" / FolderName.MERGED_OUTPUT.value
    )

    sharepoint_url_map: dict[Path, str] | None = None
    if args.location == InputLocation.SHAREPOINT:
        assert token_manager is not None
        assert drive_id is not None
        sharepoint_url_map = build_file_url_map(
            token_manager,
            drive_id,
            Path(FolderName.SHAREPOINT_INPUT_PATH) / FolderName.BILLS_INPUT,
            bills_folder,
        )

    logger.info("Starting...")

    try:
        remote_payments_folder = (
            Path(FolderName.SHAREPOINT_INPUT_PATH) / FolderName.PAYMENTS_INPUT.value
        )
        rename_payments(
            payments_folder, token_manager, drive_id, remote_payments_folder
        )
        merge_bills_and_payments(
            bills_folder,
            payments_folder,
            bills_plus_payments_folder,
            delete_processed=True,
            sharepoint_url_map=sharepoint_url_map,
            token_manager=token_manager,
            drive_id=drive_id,
            remote_folder=remote_payments_folder,
        )

        if args.location == InputLocation.SHAREPOINT:
            assert token_manager is not None
            assert drive_id is not None

            qa_folder = bills_plus_payments_folder / FolderName.QA_ERRORS.value
            copy_file(qa_report_path, qa_folder)

            upload_folder_recursive(
                token_manager,
                drive_id,
                input_folder.parent / "_output",
                FolderName.SHAREPOINT_OUTPUT_PATH,
            )

        logger.info("Finished...")

    except MainCriticalError as e:
        logger.critical(e)

    finally:
        send_qa_report_mail(
            to_email=read_secret(SecretNames.SMTP_ADMIN_EMAIL.value),
            message="Adjuntem el informe QA de l'execució.",
            qa_report_path=qa_report_path,
        )


if __name__ == "__main__":
    main()
