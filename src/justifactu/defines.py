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
from enum import StrEnum, Enum
from pathlib import Path

ROOT_FOLDER: Path = Path(__file__).resolve().parent.parent.parent
PROJECT_DIR: Path = ROOT_FOLDER  # alias kept for compatibility

DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
NOW_DATA = datetime.datetime.now()
NOW = NOW_DATA.strftime(DATETIME_FORMAT)


class InputLocation(StrEnum):
    """Input location argument possible values."""

    SHAREPOINT = "sharepoint"
    LOCAL = "local"


class FolderName(StrEnum):
    """Named folders used across the pipeline."""

    BILLS_INPUT = "FACTURES_prova"
    PAYMENTS_INPUT = "Remeses_prova"
    MERGED_OUTPUT = "FACTURES+PAGAMENTS"
    QA_ERRORS = "QA_ERRORS"
    YEAR_FOLDER_SUFFIX = "_FACTURA+PAGAMENT"
    SHAREPOINT_ROOT = "justifactu"
    INPUT = "_input"
    OUTPUT = "_output"


_SHAREPOINT_INPUT_PATH = Path(FolderName.SHAREPOINT_ROOT.value) / FolderName.INPUT.value
_SHAREPOINT_OUTPUT_PATH = (
    Path(FolderName.SHAREPOINT_ROOT.value) / FolderName.OUTPUT.value
)


class FolderPaths(Enum):
    """Composed folder paths, built from FolderName segments."""

    SHAREPOINT_INPUT_PATH = _SHAREPOINT_INPUT_PATH
    SHAREPOINT_OUTPUT_PATH = _SHAREPOINT_OUTPUT_PATH
    SHAREPOINT_BILLS_PATH = _SHAREPOINT_INPUT_PATH / FolderName.BILLS_INPUT.value
    SHAREPOINT_PAYMENTS_PATH = _SHAREPOINT_INPUT_PATH / FolderName.PAYMENTS_INPUT.value


class FileSuffix(StrEnum):
    """Named file suffixes used across the pipeline."""

    MERGED_BILL_PAYMENT = "_F_P"
    PROCESSED_PAYMENT = "_merged"


class SecretNames(StrEnum):
    """Available secret names."""

    # sharepoint
    CLIENT_ID = "CLIENT_ID"
    CLIENT_NAME = "CLIENT_NAME"
    CLIENT_SECRET = "CLIENT_SECRET"
    OBJECT_ID = "OBJECT_ID"
    SHAREPOINT_DOMAIN = "SHAREPOINT_DOMAIN"
    DRIVE_ID = "DRIVE_ID"
    SHAREPOINT_LIST_GUID = "SHAREPOINT_LIST_GUID"
    SHAREPOINT_LIST_NAME = "SHAREPOINT_LIST_NAME"
    SITE_NAME = "SITE_NAME"
    TENANT_ID = "TENANT_ID"

    # smtp
    SMTP_PASSWORD = "SMTP_PASSWORD"
    SMTP_PORT = "SMTP_PORT"
    SMTP_DEVELOPER_EMAIL = "SMTP_DEVELOPER_EMAIL"
    SMTP_SERVER = "SMTP_SERVER"
    SMTP_USERNAME = "SMTP_USERNAME"
    SMTP_ADMIN_EMAIL = "SMTP_ADMIN_EMAIL"
    SMTP_OWNER_EMAIL = "SMTP_OWNER_EMAIL"
