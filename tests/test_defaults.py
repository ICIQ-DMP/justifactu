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
from justifactu.defines import ROOT_FOLDER
from justifactu.defaults import (
    default_onedrive_data_folder,
    default_onedrive_conf_folder,
    default_secrets_folder,
)


def test_default_onedrive_data_folder():
    assert (
        default_onedrive_data_folder() == ROOT_FOLDER / "service" / "onedrive" / "data"
    )


def test_default_onedrive_conf_folder():
    assert (
        default_onedrive_conf_folder() == ROOT_FOLDER / "service" / "onedrive" / "conf"
    )


def test_default_secrets_folder():
    assert default_secrets_folder() == ROOT_FOLDER / "secrets"
