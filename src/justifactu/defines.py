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
from enum import Enum, StrEnum
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
    """Named folder paths used across the pipeline."""

    BILLS_INPUT = "FACTURES1"
    PAYMENTS_INPUT = "Remeses_prova"
    MERGED_OUTPUT = "FACTURES+PAGAMENTS"
    QA_ERRORS = "QA_ERRORS"
    YEAR_FOLDER_SUFFIX = "_FACTURA+PAGAMENT"
    SHAREPOINT_INPUT_PATH = "justifactu/_input"
    SHAREPOINT_OUTPUT_PATH = "justifactu/_output"


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


class SharepointListFields(Enum):
    """Maps semantic Python names to the internal SharePoint field names used by the Graph API."""

    ID = "id"
    REQUEST_TITLE = "Title"
    NAF = "NAF"
    TARGET_NAME = "Nomdelapersona"
    TARGET_EMAIL = "PersonaEmail"
    NIF = "DNI"
    BEGIN = "DataInici"
    END = "Datafinal"
    AUTHOR_NAME = "Sol_x00b7_licitant"
    AUTHOR_EMAIL = "SolicitantEmail"
    MERGE_SALARY_BANKPROOF = "Fusi_x00f3_NominaiJustificantBan"
    MERGE_RESULTS = "juntarpdfs"
    MERGE_RLC_RNT = "Fusi_x00f3_RLCRNT"
    WORKFLOW_STATE = "Estatworkflow"
    RESULT = "Resultat"
    ERROR_MESSAGE = "Missatge_x0020_error"
