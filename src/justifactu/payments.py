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

from .logger import get_logger
from .custom_except import ParseSAPIdException
from .pdf import extract_sap_number
from .defines import FileSuffix

log = get_logger(__name__)


# TODO: Split in two functions: One is naif, and creates a dict of content inside a folder dict[str, Path].
# the other function is specialized and receives this dict and parses it so that only pdf files matching SAP ID remain
# in the dict.
def index_payments(payments_folder: Path) -> dict[str, Path]:
    """Scans the payments folder and returns a mapping of SAP numbers to file paths."""
    payment_map: dict[str, Path] = {}

    for payment_path in payments_folder.rglob("*.pdf"):
        if not payment_path.is_file():
            continue

        if payment_path.stem.endswith(FileSuffix.PROCESSED_PAYMENT):
            log.info(f"Skipping {payment_path} because it is already merged")
            continue

        try:
            sap_number = extract_sap_number(payment_path.name)
            payment_map[sap_number] = payment_path
        except ParseSAPIdException:
            log.error(
                f"Failed to parse SAP ID from {payment_path}: {payment_path.name}"
            )

    return payment_map
