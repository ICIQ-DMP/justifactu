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

"""Date formatting and document-filename parsing helpers."""

from datetime import datetime

from . import logger

log = logger.get_logger(__name__)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def unparse_month(d: datetime) -> str:
    """Return the zero-padded two-digit month string."""
    return d.strftime("%m")


def unparse_year_month(d: datetime) -> str:
    """Return a six-character YYYYMM string."""
    return d.strftime("%Y%m")


def unparse_year_month_short(d: datetime) -> str:
    """Return a four-character YYMM string."""
    return d.strftime("%y%m")


def unparse_date(d: datetime, separator: str = "-") -> str:
    """Return a MM<sep>YYYY string."""
    return d.strftime("%m") + separator + d.strftime("%Y")


def unparse_full_date(d: datetime, separator: str = "-") -> str:
    """Return a DD<sep>MM<sep>YYYY string."""
    return (
        d.strftime("%d") + separator + d.strftime("%m") + separator + d.strftime("%Y")
    )
