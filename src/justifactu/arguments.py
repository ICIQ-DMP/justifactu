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

import argparse
import sys
from pathlib import Path

from justifactu.custom_except import ArgumentInputLocationError
from justifactu.defines import ROOT_FOLDER, InputLocation


def parse_input_type(value: str) -> InputLocation:
    if value == InputLocation.SHAREPOINT.value:
        return InputLocation.SHAREPOINT
    elif value == InputLocation.LOCAL.value:
        return InputLocation.LOCAL
    else:
        raise ArgumentInputLocationError(
            'The type supplied for input type "' + value + '" is not defined.'
        )


def parse_input_location(value: str) -> Path:
    path = Path(value)
    if not path.exists():
        raise ValueError(f"Path {value} does not exist")
    if not path.is_dir():
        raise ValueError(f"Path {value} is not a directory")
    return path


def parse_arguments() -> argparse.Namespace:
    """Parse and validate command-line arguments"""
    parser = argparse.ArgumentParser(description="Justifactu")

    parser.add_argument(
        "-l",
        "--location",
        type=parse_input_type,
        required=False,
        default=InputLocation.SHAREPOINT,
        help='Location of the input data. Possible values are: "sharepoint" to download from '
        'sharepoint location and "local" to use the local file system storage and read the input'
        " folder in the repository root folder.",
    )
    parser.add_argument(
        "-L",
        "--input-location",
        type=parse_input_location,
        required=False,
        default=Path(
            ROOT_FOLDER,
            "service",
            "onedrive",
            "data",
            "justifactu",
            "_input",
        ),
        help="Path location of input data. If used, --location local is assumed.",
    )

    args = parser.parse_args()

    return args


def process_parse_arguments() -> argparse.Namespace:
    common = (
        "Error parsing arguments. Program aborting. The arguments are: "
        + str(sys.argv)
        + "The program is in a uninitialized state and cannot proceed. This error will be "
        "notified to the admin via log file. We can't create log file in user author folder "
        "because user author could not be parsed."
    )
    try:
        args = parse_arguments()

    except argparse.ArgumentTypeError as e:
        print("Arguments could not have been parsed. Internal error is " + e.__str__())
        print(common)
        exit(5)

    return args
