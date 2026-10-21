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

from justifactu.onedrive_sync import (
    run_onedrive_sync,
    run_onedrive_auth,
)
from justifactu.arguments import process_parse_arguments

from justifactu.defines import (
    NOW,
    SecretNames,
    SyncDirection,
    InputLocation,
)
from justifactu.paths import merged_bills_and_payments_folder, qa_errors_folder
from justifactu.logger import (
    LOGS_FOLDER,
    configure_logging_from_settings,
    get_logger,
    get_user_log_path,
)
from justifactu.filesystem import copy_file
from justifactu.mail import send_qa_report_mail
from justifactu.process import run_all_phases, run_phase
from justifactu.custom_except import MainCriticalError
from justifactu.secret import read_secret
from justifactu.sharepoint import connect_sharepoint, download_input_folder

log = get_logger(__name__)


def main() -> None:
    """"""
    qa_report_path = LOGS_FOLDER / (NOW + "_qa_report.log")
    configure_logging_from_settings(qa_files_log_file=qa_report_path)

    args = process_parse_arguments()
    if args.phase is not None:
        run_phase(args.phase, args.runtime_location, args.mode)
        return

    confdir = args.onedrive_conf_folder

    log.info("Starting...")

    if args.auth and args.location == InputLocation.SHAREPOINT:
        run_onedrive_auth(
            confdir,
            data_folder=args.onedrive_data_folder,
        )
        return

    try:
        try:
            run_onedrive_sync(
                confdir,
                direction=SyncDirection.DOWNLOAD.value,
                single_dir=args.sharepoint_sync_folder,
                data_folder=args.onedrive_data_folder,
                dry_run=args.dry_run,
            )
        except MainCriticalError as e:
            log.warning(
                f"OneDrive download sync failed ({e}); falling back to a direct "
                "Microsoft Graph download."
            )
            try:
                token_manager, _, drive_id = connect_sharepoint()
                log.warning("Downloading OneDrive content using API as fallback")
                download_input_folder(
                    token_manager,
                    drive_id,
                    args.sharepoint_sync_folder,
                    args.runtime_location,
                )
            except Exception as fallback_error:
                raise MainCriticalError(
                    f"Graph API fallback download also failed: {fallback_error}"
                ) from fallback_error

        run_all_phases(args.runtime_location, args.mode)

        bills_plus_payments_folder = merged_bills_and_payments_folder(
            args.runtime_location, args.mode
        )
        qa_folder = qa_errors_folder(bills_plus_payments_folder)
        qa_folder.mkdir(parents=True, exist_ok=True)
        copy_file(qa_report_path, qa_folder)
        regular_log_path = LOGS_FOLDER / (NOW + ".log")
        copy_file(regular_log_path, qa_folder)

        run_onedrive_sync(
            confdir,
            direction=SyncDirection.UPLOAD.value,
            single_dir=args.sharepoint_sync_folder,
            data_folder=args.onedrive_data_folder,
            dry_run=args.dry_run,
        )
        log.info("Finished...")

    except MainCriticalError as e:
        log.critical(e)
        exit(1)

    finally:
        try:
            send_qa_report_mail(
                to_email=read_secret(SecretNames.SMTP_OWNER_EMAIL.value),
                message="Adjuntem el informe QA de l'execució.",
                qa_report_path=qa_report_path,
                additional_attachments=[get_user_log_path()],
            )
        except Exception as e:
            log.error(f"Failed to send QA report email: {e}")
