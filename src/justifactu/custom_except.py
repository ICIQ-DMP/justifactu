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

"""Domain-specific exception hierarchy for justifactu."""


class ArgumentInputLocationError(Exception):
    """Raised when an input location argument or cannot be parsed."""


class ParseSAPIdException(Exception):
    """Raised when a SAP id cannot be parsed from a file."""


class SecretCouldNotBeReadFromAnySourceError(Exception):
    """Raised when a secret cannot be read from any source."""


class MergingBillWithPaymentError(Exception):
    """Raised when merging bills with payment cannot be made."""


class FileDeletionError(Exception):
    """Raised when a file cannot be deleted."""


class MainCriticalError(Exception):
    """Raised when critical error occurs on main procedure."""


class SkippedPdfRenamingInvalidSapId(Exception):
    """Raised when pdf is skipped in name change due to invalid SAP id value."""


class UnexpectedRenamingError(Exception):
    """Raised when renaming failed due to unexpected circumstances."""


class VaultSecretEmpty(Exception):
    """Raised when secret is empty."""
