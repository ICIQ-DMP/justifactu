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

from justifactu.defines import Mode, FolderName, FileSuffix
from justifactu.paths import (
    bills_folder,
    payments_folder,
    merged_bills_and_payments_folder,
    qa_errors_folder,
    year_merged_folder,
    sharepoint_sync_folder,
)


def test_bills_folder():
    assert bills_folder(Path("/base")) == Path("/base") / FolderName.BILLS.value


def test_payments_folder():
    assert payments_folder(Path("/base")) == Path("/base") / FolderName.PAYMENTS.value


def test_merged_output_folder():
    assert merged_bills_and_payments_folder(Path("/base")) == (
        Path("/base") / FolderName.BILLS_AND_PAYMENTS.value
    )


def test_qa_errors_folder():
    base = Path("/base") / FolderName.BILLS_AND_PAYMENTS.value
    assert qa_errors_folder(base) == base / FolderName.QA_ERRORS.value


def test_year_merged_folder():
    base = Path("/base") / FolderName.BILLS_AND_PAYMENTS.value
    assert year_merged_folder(base, "2025") == base / (
        "2025" + FileSuffix.YEAR_FOLDER_SUFFIX.value
    )


def test_sharepoint_sync_folder_prod():
    assert sharepoint_sync_folder(Mode.PROD) == (
        Path(FolderName.SHAREPOINT_ROOT.value) / FolderName.RUNTIME_PROD.value
    )


def test_sharepoint_sync_folder_test():
    assert sharepoint_sync_folder(Mode.TEST) == (
        Path(FolderName.SHAREPOINT_ROOT.value) / FolderName.RUNTIME_TEST.value
    )


def test_sharepoint_sync_folder_dev_uses_test_runtime():
    assert sharepoint_sync_folder(Mode.DEV) == (
        Path(FolderName.SHAREPOINT_ROOT.value) / FolderName.RUNTIME_TEST.value
    )
