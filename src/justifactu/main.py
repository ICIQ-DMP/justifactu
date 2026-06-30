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
from justifactu.defines import NOW, InputLocation, FolderName
from justifactu.logger import (
    ADMIN_LOG_FOLDER,
    configure_logging_from_settings,
    get_logger,
)
from justifactu.process import merge_bills_and_payments
from justifactu.pdf import rename_payments
from justifactu.custom_except import MainCriticalError
from justifactu.sharepoint import (
    _connect_sharepoint,
    download_input_folder,
    upload_folder_recursive,
)

logger = get_logger(__name__)


def main() -> None:
    """"""
    configure_logging_from_settings(
        moved_files_log_file=ADMIN_LOG_FOLDER / (NOW + "_qa_report.log"),
    )

    args = process_parse_arguments()

    default_input_folder = Path("./service/onedrive/data/justifactu/_input")
    token_manager = None
    site_id = None
    drive_id = None
    # TODO comentar implementació amb Aleix
    if args.location == InputLocation.LOCAL:
        input_folder = args.input_location or default_input_folder
    else:
        input_folder = default_input_folder
        token_manager, site_id, drive_id = _connect_sharepoint()
        download_input_folder(
            token_manager,
            drive_id,
            Path(FolderName.SHAREPOINT_INPUT_PATH),
            input_folder,
        )
    bills_folder = input_folder / FolderName.BILLS_INPUT
    payments_folder = input_folder / FolderName.PAYMENTS_INPUT
    bills_plus_payments_folder = (
        input_folder.parent / "_output" / FolderName.MERGED_OUTPUT
    )

    logger.info("Starting...")

    try:
        rename_payments(payments_folder)
        merge_bills_and_payments(
            bills_folder,
            payments_folder,
            bills_plus_payments_folder,
            delete_processed=True,
        )

        if args.location == InputLocation.SHAREPOINT:
            assert token_manager is not None
            assert drive_id is not None
            upload_folder_recursive(
                token_manager,
                drive_id,
                input_folder.parent / "_output",
                FolderName.SHAREPOINT_OUTPUT_PATH,
            )

        logger.info("Finished...")

    except MainCriticalError as e:
        logger.critical(e)


if __name__ == "__main__":
    main()
