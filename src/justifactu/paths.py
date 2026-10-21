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

"""Composed paths, built from already-resolved base directories and FolderName segments."""

from pathlib import Path

from .defines import FileSuffix, FolderName, Mode


def bills_folder(input_folder: Path) -> Path:
    return input_folder / FolderName.BILLS.value


def payments_folder(input_folder: Path) -> Path:
    return input_folder / FolderName.PAYMENTS.value


def merged_bills_and_payments_folder(input_folder: Path) -> Path:
    return input_folder / FolderName.BILLS_AND_PAYMENTS.value


def qa_errors_folder(merged_output_folder: Path) -> Path:
    return merged_output_folder / FolderName.QA_ERRORS.value


def logs_folder(merged_output_folder: Path) -> Path:
    return merged_output_folder / FolderName.LOGS.value


def year_merged_folder(merged_output_folder: Path, year: str) -> Path:
    return merged_output_folder / (year + FileSuffix.YEAR_FOLDER_SUFFIX.value)


def sharepoint_sync_folder(mode: Mode) -> Path:
    runtime = FolderName.RUNTIME_PROD if mode == Mode.PROD else FolderName.RUNTIME_TEST
    return Path(FolderName.SHAREPOINT_ROOT.value) / runtime.value
