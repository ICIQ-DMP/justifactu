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

from justifactu.filesystem import list_dir


def test_list_dir_empty_directory(tmp_path):
    result = list_dir(tmp_path)
    assert result == []


def test_list_dir_with_files(tmp_path):
    (tmp_path / "a.txt").touch()
    (tmp_path / "b.txt").touch()

    result = list_dir(tmp_path)
    names = {p.name for p in result}

    assert names == {"a.txt", "b.txt"}


def test_list_dir_returns_path_objects(tmp_path):
    from pathlib import Path

    (tmp_path / "x.txt").touch()
    result = list_dir(tmp_path)
    assert all(isinstance(p, Path) for p in result)


def test_list_dir_not_a_directory_raises(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.touch()
    with pytest.raises(ValueError):
        list_dir(file_path)


def test_list_dir_nonexistent_path_raises(tmp_path):
    nonexistent = tmp_path / "missing"
    with pytest.raises(ValueError):
        list_dir(nonexistent)
