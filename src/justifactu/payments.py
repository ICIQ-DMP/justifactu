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

from .SAP_ID import SAP_ID, parse_sap_id_from_string
from .logger import get_logger
from .custom_except import ParseSAPIdException
from .defines import FileSuffix

log = get_logger(__name__)


# TODO move to filesystem.py


def index_payments(folder_map: dict[str, Path]) -> dict[SAP_ID, Path]:
    payment_map: dict[SAP_ID, Path] = {}

    for filename, payment_path in folder_map.items():

        if payment_path.suffix.lower() != ".pdf":
            log.warning(f"Skipping {payment_path} because it is not a PDF")
            continue

        if payment_path.stem.endswith(FileSuffix.PROCESSED_PAYMENT):
            log.info(f"Skipping {payment_path} because it is already processed")
            continue

        try:
            sap_number = parse_sap_id_from_string(filename)
            payment_map[sap_number] = payment_path

        except ParseSAPIdException:
            log.error(f"Failed to parse SAP ID from {payment_path}: {filename}")

    return payment_map
