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

from .defines import FolderName, Mode


def bills_folder(input_folder: Path, mode: Mode) -> Path:
    if mode == Mode.PROD:
        return input_folder / FolderName.BILLS_INPUT_PROD.value
    return input_folder / FolderName.BILLS_INPUT_TEST.value


def payments_folder(input_folder: Path, mode: Mode) -> Path:
    if mode == Mode.PROD:
        return input_folder / FolderName.PAYMENTS_INPUT_PROD.value
    return input_folder / FolderName.PAYMENTS_INPUT_TEST.value


def merged_bills_and_payments_folder(input_folder: Path, mode: Mode) -> Path:
    if mode == Mode.PROD:
        return input_folder / FolderName.MERGED_OUTPUT_PROD.value
    return input_folder / FolderName.MERGED_OUTPUT_TEST.value


def qa_errors_folder(merged_output_folder: Path) -> Path:
    return merged_output_folder / FolderName.QA_ERRORS.value


def year_merged_folder(merged_output_folder: Path, year: str) -> Path:
    return merged_output_folder / (year + FolderName.YEAR_FOLDER_SUFFIX.value)


def sharepoint_sync_folder() -> Path:
    return Path(FolderName.SHAREPOINT_ROOT_FOLDER.value) / FolderName.RUNTIME.value
