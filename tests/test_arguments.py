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

import pytest

from justifactu.arguments import parse_input_location, parse_input_type
from justifactu.custom_except import ArgumentInputLocationError
from justifactu.defines import InputLocation

# ── parse_input_type ─────────────────────────────────────────────────────────


def test_parse_input_type_sharepoint():
    assert parse_input_type(InputLocation.SHAREPOINT.value) == InputLocation.SHAREPOINT


def test_parse_input_type_local():
    assert parse_input_type(InputLocation.LOCAL.value) == InputLocation.LOCAL


def test_parse_input_type_invalid_raises():
    with pytest.raises(ArgumentInputLocationError):
        parse_input_type("ftp")


# ── parse_input_location ─────────────────────────────────────────────────────


def test_parse_input_location_valid_dir(tmp_path):
    result = parse_input_location(str(tmp_path))
    assert result == tmp_path


def test_parse_input_location_nonexistent_raises(tmp_path):
    nonexistent = tmp_path / "does_not_exist"
    with pytest.raises(ArgumentInputLocationError, match="does not exist"):
        parse_input_location(str(nonexistent))


def test_parse_input_location_file_raises(tmp_path):
    file_path = tmp_path / "a_file.txt"
    file_path.touch()
    with pytest.raises(ArgumentInputLocationError, match="not a directory"):
        parse_input_location(str(file_path))
