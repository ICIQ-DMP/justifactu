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

import os
import shutil
from pathlib import Path
from typing import List

from .logger import get_logger

log = get_logger(__name__)


def list_dir(input_folder: Path) -> List[Path]:
    """Returns a list of all file names in the ./input/salaries directory."""
    # Ensure the input_folder is a valid directory
    if not input_folder.is_dir():
        raise ValueError(
            "input folder "
            + str(input_folder)
            + " in list_files function is not a directory or can't be accessed"
        )
    return [item for item in input_folder.rglob("*") if item.is_file()]


def copy_file(origin_path: Path, target_path: Path) -> None:
    """Copies a file to another location"""
    # Check to avoid overwriting a file.
    dest_file = target_path / origin_path.name if target_path.is_dir() else target_path

    if dest_file.exists():
        raise FileExistsError(f"Destination file already exists: {dest_file}")

    dest_file.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy(origin_path, dest_file)

    log.info(f"Copied: {origin_path} into {target_path}")


def move_file(origin_path: Path, target_path: Path) -> None:
    """Moves a file to another location"""
    target_path.mkdir(parents=True, exist_ok=True)
    dest_file = target_path / origin_path.name

    try:
        shutil.move(origin_path, dest_file)
        log.info(f"Moved: {origin_path} into {target_path}")

    except FileExistsError:
        log.warning(f"Destination file already exists: {dest_file}")

    except Exception as e:
        log.exception(f"Unexpected error: {e}")


def change_file_name(file: Path, new_name: str) -> Path | None:
    """Changes the name of a file"""

    if not file.exists():
        log.warning(f"File not found at {file}")
        raise FileNotFoundError(f"File not found at {file}")

    new_path = file.with_stem(new_name)

    if new_path.exists():
        log.warning(f"A file named {new_path.name} already exists.")

    file.rename(new_path)
    log.info(f"Renamed: {file} to {new_path}")
    return new_path


def read_env_var(var_name: str) -> str:
    """Reads an environment variable.

    Args:
        var_name (str): Name of the environment variable.

    Returns:
        str: The value of the environment variable if valid.

    Raises:
        KeyError: If the environment variable does not exist.
        ValueError: If the environment variable is empty or contains only whitespace.
    """
    if var_name not in os.environ:
        raise KeyError(f"The environment variable '{var_name}' does not exist.")

    value = os.environ[var_name]

    if not value:
        raise ValueError(f"The environment variable '{var_name}' is empty.")

    return value


def read_file_content(file_path: Path) -> str:
    """Read a file and return its non-empty content.

    Args:
        file_path: Path to the file.

    Returns:
        The file content as a string.

    Raises:
        ValueError: If the file exists but is empty.
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read.
    """
    content = read_file(file_path)
    if not content:
        raise ValueError(f"The file '{file_path}' is empty.")
    return content


def read_file(file_path: Path) -> str:
    """Reads a file and returns its content.

    Args:
        file_path (Path): Path to the file.

    Returns:
        str: The content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read due to permission issues.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"The file '{file_path}' does not exist.")

    if not os.access(file_path, os.R_OK):
        raise PermissionError(
            f"The file '{file_path}' cannot be read. Check permissions."
        )

    with open(file_path, "r") as file:
        content = file.read()

    return content


def index_folder(folder_path: Path) -> dict[str, Path]:
    """Returns a mapping of filename to path for every file in the folder."""
    return {entry.name: entry for entry in folder_path.rglob("*") if entry.is_file()}
