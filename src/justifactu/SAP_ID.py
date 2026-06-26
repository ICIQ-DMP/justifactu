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
import re

from .custom_except import ParseSAPIdException
from .logger import get_logger

log = get_logger(__name__)

pattern = r"(20\d{2})(\d{6})"


class SAP_ID:
    def __init__(self, raw_sap_id: str) -> None:
        match = re.fullmatch(pattern, raw_sap_id)

        if not match:
            raise ParseSAPIdException(f"Invalid SAP ID: {raw_sap_id}")
        self.sap_id = raw_sap_id
        self.year = match.group(1)

    def __str__(self) -> str:
        return str(self.sap_id)


# TODO change name and function to parse_sap_id_from_string
def sap_id_from_filename(filename: str) -> SAP_ID:
    """Extracts digits from a filename and returns a validated SAP instance."""
    matches = re.findall(pattern, filename)

    if len(matches) > 1:
        raise ParseSAPIdException(
            f"Found multiple matches for {filename}, assuming first match"
        )

    elif len(matches) == 0:
        log.error(f"No matches found for {filename}")
        raise ParseSAPIdException(f"Invalid SAP ID: {filename}")

    cleaned_sap_id = "".join(matches[0])

    return SAP_ID(cleaned_sap_id)
