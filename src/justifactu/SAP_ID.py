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

# TODO: I made this variable public by exposing it, you were using three different versions of it!
# TODO: match with more restriction: First 2 digits of year are going to be 20 always (support until 2099)
pattern = r"(\d{4})(\d{6})"


class SAP_ID:
    def __init__(self, raw_sap_id: str) -> None:
        match = re.fullmatch(pattern, raw_sap_id)

        if not match:
            raise ParseSAPIdException(f"Invalid SAP ID: {raw_sap_id}")
        self.sap_id = raw_sap_id
        self.year = match.group(1)

    def __str__(self) -> str:
        return str(self.sap_id)

    # TODO: The following two methods break the single responsibility principle: SAP class does not need to know about
    # files or bills. Move to bill.py. Also, I think you only need one of these methods
    @classmethod
    def from_filename(cls, filename: str) -> "SAP_ID":
        """Extracts digits from a filename and returns a validated SAP instance."""
        print("\n\nEntering SAP.from_filename")
        print(filename)
        matches = re.findall(pattern, filename)

        if len(matches) > 1:
            # TODO: throw exception or make assumption
            print("there is more than one ID, assuming first ID")
        elif len(matches) == 0:
            raise ParseSAPIdException(f"Invalid SAP ID: {filename}")

        cleaned_sap_id = "".join(matches[0])

        return cls(cleaned_sap_id)

    @classmethod
    def matches_bill_filename(cls, stem: str) -> bool:
        """Returns True if stem matches the expected bill filename format (e.g. 'F 1234567890')."""
        filename_pattern = r"F\s" + pattern
        return bool(re.fullmatch(filename_pattern, stem))
