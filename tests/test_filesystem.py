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

from justifactu.filesystem import list_dir, copy_file, change_file_name, move_file


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


# ── copy_file ─────────────────────────────────────────────────────────────────


def test_copy_file_to_new_path(tmp_path):
    src = tmp_path / "src.pdf"
    src.touch()
    dst = tmp_path / "dst.pdf"

    copy_file(src, dst)

    assert dst.exists()
    assert src.exists()  # original is preserved


def test_copy_file_into_directory(tmp_path):
    src = tmp_path / "src.pdf"
    src.touch()
    dest_dir = tmp_path / "subdir"
    dest_dir.mkdir()

    copy_file(src, dest_dir)

    assert (dest_dir / "src.pdf").exists()


def test_copy_file_destination_exists_raises(tmp_path):
    src = tmp_path / "src.pdf"
    src.touch()
    dst = tmp_path / "dst.pdf"
    dst.touch()

    with pytest.raises(FileExistsError):
        copy_file(src, dst)


def test_copy_file_creates_parent_directories(tmp_path):
    src = tmp_path / "src.pdf"
    src.touch()
    dst = tmp_path / "a" / "b" / "dst.pdf"

    copy_file(src, dst)

    assert dst.exists()


# ── move_file ─────────────────────────────────────────────────────────────────


def test_move_file_success(tmp_path):
    src = tmp_path / "src.pdf"
    src.touch()
    dest_dir = tmp_path / "subdir"

    move_file(src, dest_dir)

    assert (dest_dir / "src.pdf").exists()
    assert not src.exists()


def test_move_file_creates_destination_directory(tmp_path):
    src = tmp_path / "src.pdf"
    src.touch()
    dest_dir = tmp_path / "new" / "nested"

    move_file(src, dest_dir)

    assert (dest_dir / "src.pdf").exists()


# ── change_file_name ──────────────────────────────────────────────────────────


def test_change_file_name_success(tmp_path):
    original = tmp_path / "old_name.pdf"
    original.touch()

    result = change_file_name(original, "new_name")

    assert result == tmp_path / "new_name.pdf"
    assert result.exists()
    assert not original.exists()


def test_change_file_name_nonexistent_returns_none(tmp_path):
    missing = tmp_path / "missing.pdf"
    result = change_file_name(missing, "anything")
    assert result is None


def test_change_file_name_collision_returns_none(tmp_path):
    original = tmp_path / "original.pdf"
    original.touch()
    conflict = tmp_path / "conflict.pdf"
    conflict.touch()

    result = change_file_name(original, "conflict")
    assert result is None
