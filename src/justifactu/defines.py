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

import datetime
from enum import Enum
from pathlib import Path

ROOT_FOLDER: Path = Path(__file__).resolve().parent.parent.parent
PROJECT_DIR: Path = ROOT_FOLDER  # alias kept for compatibility

DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
NOW_DATA = datetime.datetime.now()
NOW = NOW_DATA.strftime(DATETIME_FORMAT)


class InputLocation(str, Enum):
    """Input location argument possible values."""

    SHAREPOINT = "sharepoint"
    LOCAL = "local"


class FolderName(str, Enum):
    """Named folder paths used across the pipeline."""

    BILLS_INPUT = "FACTURES"
    PAYMENTS_INPUT = "Remeses"
    MERGED_OUTPUT = "FACTURES+PAGAMENTS"
    QA_ERRORS = "QA_ERRORS"
    YEAR_FOLDER_SUFFIX = "_FACTURA+PAGAMENT"


class FileSuffix(str, Enum):
    """Named file suffixes used across the pipeline."""

    MERGED_BILL_PAYMENT = "_F_P"
    PROCESSED_PAYMENT = "_merged"


class SecretNames(str, Enum):
    """Available secret names."""

    SHAREPOINT_DOMAIN = "SHAREPOINT_DOMAIN"
    SITE_NAME = "SITE_NAME"
    SMTP_OWNER_EMAIL = "SMTP_OWNER_EMAIL"
    SMTP_USERNAME = "SMTP_USERNAME"
    SMTP_PASSWORD = "SMTP_PASSWORD"
    SMTP_SERVER = "SMTP_SERVER"
    SMTP_PORT = "SMTP_PORT"
    SMTP_DEVELOPER_EMAIL = "SMTP_DEVELOPER_EMAIL"
