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
import sys

from justifactu.arguments import (
    parse_input_location,
    parse_input_type,
    parse_arguments,
    parse_file,
    process_parse_arguments,
)
from justifactu.custom_except import ArgumentInputLocationError
from justifactu.defines import InputLocation, Mode

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


# ── parse_file ─────────────────────────────────────────────────────


def test_parse_file_valid_file(tmp_path):
    file_path = tmp_path / "ledger.xlsx"
    file_path.touch()
    assert parse_file(str(file_path)) == file_path


def test_parse_file_nonexistent_raises(tmp_path):
    missing = tmp_path / "missing.xlsx"
    with pytest.raises(ArgumentInputLocationError, match="does not exist"):
        parse_file(str(missing))


def test_parse_file_directory_raises(tmp_path):
    with pytest.raises(ArgumentInputLocationError, match="not a file"):
        parse_file(str(tmp_path))


# ── --auth ────────────────────────────────────────────────────────────────────


def test_auth_defaults_to_false_when_absent(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    args = parse_arguments()
    assert args.auth is False


def test_auth_sets_true_with_no_value(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--auth"])
    args = parse_arguments()
    assert args.auth is True


# ── --mode ────────────────────────────────────────────────────────────────────


def test_mode_defaults_to_test_when_absent(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    args = parse_arguments()
    assert args.mode == Mode.TEST


def test_mode_prod_explicit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--mode", "prod"])
    args = parse_arguments()
    assert args.mode == Mode.PROD


def test_mode_test_explicit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--mode", "test"])
    args = parse_arguments()
    assert args.mode == Mode.TEST


# ── --ledger-path ─────────────────────────────────────────────────────


def test_ledger_path_defaults_to_none_when_absent(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    args = parse_arguments()
    assert args.ledger_path is None


def test_ledger_path_parses_given_file(monkeypatch, tmp_path):
    ledger = tmp_path / "ledger.xlsx"
    ledger.touch()
    monkeypatch.setattr(sys, "argv", ["prog", "--ledger-path", str(ledger)])
    args = parse_arguments()
    assert args.ledger_path == ledger


# ── process_parse_arguments ─────────────────────────────────────────────────────


def test_process_parse_arguments_requires_ledger_for_full_run(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--onedrive-data-folder",
            str(tmp_path / "data"),
            "--sharepoint-sync-folder",
            str(tmp_path / "sync"),
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        process_parse_arguments()
    assert exc_info.value.code == 5


def test_process_parse_arguments_requires_ledger_for_phase_1(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--phase",
            "1",
            "--onedrive-data-folder",
            str(tmp_path / "data"),
            "--sharepoint-sync-folder",
            str(tmp_path / "sync"),
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        process_parse_arguments()
    assert exc_info.value.code == 5


def test_process_parse_arguments_phase_2_does_not_require_ledger(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--phase",
            "2",
            "--onedrive-data-folder",
            str(tmp_path / "data"),
            "--sharepoint-sync-folder",
            str(tmp_path / "sync"),
        ],
    )
    args = process_parse_arguments()
    assert args.ledger_path is None


def test_process_parse_arguments_full_run_with_ledger_succeeds(monkeypatch, tmp_path):
    ledger = tmp_path / "ledger.xlsx"
    ledger.touch()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--ledger-path",
            str(ledger),
            "--onedrive-data-folder",
            str(tmp_path / "data"),
            "--sharepoint-sync-folder",
            str(tmp_path / "sync"),
        ],
    )
    args = process_parse_arguments()
    assert args.ledger_path == ledger
