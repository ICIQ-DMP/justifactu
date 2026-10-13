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

"""Fallback Path values for CLI flags, computed from ROOT_FOLDER and FolderName segments."""

from pathlib import Path

from .defines import ROOT_FOLDER, FolderName


def default_onedrive_data_folder() -> Path:
    return (
        ROOT_FOLDER
        / FolderName.SERVICE.value
        / FolderName.ONEDRIVE.value
        / FolderName.ONEDRIVE_DATA.value
    )


def default_onedrive_conf_folder() -> Path:
    return (
        ROOT_FOLDER
        / FolderName.SERVICE.value
        / FolderName.ONEDRIVE.value
        / FolderName.ONEDRIVE_CONF.value
    )


def default_secrets_folder() -> Path:
    return ROOT_FOLDER / FolderName.SECRETS.value
