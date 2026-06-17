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

from justifactu.custom_except import ParseSAPIdException
from justifactu.logger import get_logger

log = get_logger(__name__)


class SAP:
    def __init__(self, raw_sap_id: str) -> None:
        pattern = r"(\d{4})(\d{6})"
        match = re.fullmatch(pattern, raw_sap_id)

        if not match:
            raise ParseSAPIdException(f"Invalid SAP ID: {raw_sap_id}")
        self.sap_id = raw_sap_id
        self.year = match.group(1)

    def __str__(self) -> str:
        return str(self.sap_id)

    @classmethod
    def from_filename(cls, filename: str) -> "SAP":
        """Extracts digits from a filename and returns a validated SAP instance."""
        clean_id = re.sub(r"\D", "", filename)

        return cls(clean_id)

    @classmethod
    def matches_bill_filename(cls, stem: str) -> bool:
        """Returns True if stem matches the expected bill filename format (e.g. 'F 1234567890')."""
        return bool(re.fullmatch(r"F\s\d{10}", stem))
