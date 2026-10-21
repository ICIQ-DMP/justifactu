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
from enum import StrEnum
from pathlib import Path

ROOT_FOLDER: Path = Path(__file__).resolve().parent.parent.parent

DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
NOW_DATA = datetime.datetime.now()
NOW = NOW_DATA.strftime(DATETIME_FORMAT)


class InputLocation(StrEnum):
    """Input location argument possible values."""

    SHAREPOINT = "sharepoint"
    LOCAL = "local"


class SyncDirection(StrEnum):
    """Sync direction argument possible values."""

    DOWNLOAD = "download"
    UPLOAD = "upload"


class Mode(StrEnum):
    """Run mode: selects between production and test folder names."""

    PROD = "prod"
    TEST = "test"


class FolderName(StrEnum):
    """Named folders used across the pipeline."""

    # Sharepoint folders
    SHAREPOINT_ROOT = "justifactu"

    RUNTIME = "runtime"

    BILLS_PROD = "FACTURES"
    BILLS_TEST = "FACTURES_prova"

    PAYMENTS_PROD = "Remeses"
    PAYMENTS_TEST = "Remeses_prova"

    BILLS_AND_PAYMENTS_PROD = "FACTURES+PAGAMENTS"
    BILLS_AND_PAYMENTS_TEST = "FACTURES+PAGAMENTS_prova"

    QA_ERRORS = "QA_ERRORS"

    # Repository folders
    LOGS = "logs"
    SECRETS = "secrets"

    SERVICE = "service"
    ONEDRIVE = "onedrive"
    ONEDRIVE_DATA = "data"
    ONEDRIVE_CONF = "conf"


class Phase(StrEnum):
    PHASE_1 = "1"
    PHASE_2 = "2"
    PHASE_3 = "3"


class FileSuffix(StrEnum):
    """Named file suffixes used across the pipeline."""

    MERGED_BILL_PAYMENT = "_F_P"
    PROCESSED_PAYMENT = "_merged"
    YEAR_FOLDER_SUFFIX = "_FACTURA+PAGAMENT"


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
    SMTP_SERVER = "SMTP_SERVER"
    SMTP_USERNAME = "SMTP_USERNAME"
    SMTP_ADMIN_EMAIL = "SMTP_ADMIN_EMAIL"
    SMTP_OWNER_EMAIL = "SMTP_OWNER_EMAIL"
    SMTP_DEVELOPER_EMAIL = "SMTP_DEVELOPER_EMAIL"
