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
from pathlib import Path
from typing import Any

from justifactu.arguments import process_parse_arguments
from justifactu.defines import NOW
from justifactu.logger import (
    ADMIN_LOG_FOLDER,
    configure_logging_from_settings,
    get_logger,
)
from justifactu.pdf import merge_bills_and_payments, rename_payments

logger = get_logger(__name__)


def compute_path(partial_path: str, extension: str) -> Path:
    suffix = 1
    output_path = Path(partial_path + extension)
    while output_path.exists():
        if suffix < 100:
            str_suffix = "00" + str(suffix)
        elif suffix < 10:
            str_suffix = "0" + str(suffix)
        else:
            str_suffix = str(suffix)
        output_path = Path(partial_path + "_" + str_suffix + extension)
        suffix += 1

    return output_path


def datetime_range(begin: datetime, end: datetime) -> list[datetime]:
    current = datetime(begin.year, begin.month, 1)

    result = []
    while current <= end:
        result.append(
            datetime.strptime(str(current.year * 100 + current.month), "%Y%m")
        )
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    return result


def reverse_dict(d: dict[Any, Any]) -> dict[Any, Any]:
    r = {}
    for key in d.keys():
        r[d[key]] = key
    return r


def main() -> None:
    """"""
    configure_logging_from_settings(
        moved_files_log_file=ADMIN_LOG_FOLDER / (NOW + "_qa_report.log"),
    )

    args = process_parse_arguments()

    if args.input_location:
        input_folder = Path(args.input_location)
    else:
        input_folder = Path("./service/onedrive/data/justifactu/_input")
    bills_folder = input_folder / "FACTURES"
    payments_folder = input_folder / "Remeses"
    bills_plus_payments_folder = input_folder.parent / "_output" / "FACTURES+PAGAMENTS"

    logger.info("Starting...")

    try:
        rename_payments(payments_folder)
        merge_bills_and_payments(
            bills_folder,
            payments_folder,
            bills_plus_payments_folder,
            delete_processed=True,
        )
        logger.info("Finished...")

    except Exception as e:
        logger.critical(e)


if __name__ == "__main__":
    main()
