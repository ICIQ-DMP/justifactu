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
from justifactu.defines import InputLocation, ROOT_FOLDER, Phase


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
        raise ArgumentInputLocationError(f"Path {value} does not exist")
    if not path.is_dir():
        raise ArgumentInputLocationError(f"Path {value} is not a directory")
    return path


def parse_directory(value: str) -> Path:
    path = Path(value)
    if not path.exists():
        path.mkdir(parents=True)
    if not path.is_dir():
        raise ArgumentInputLocationError(f"Path {value} is not a directory")
    return path


def parse_phase(value: str) -> Phase:
    try:
        return Phase(value)
    except ValueError:
        raise ArgumentInputLocationError(
            'The phase supplied "' + value + '" is not defined.'
        )


def parse_arguments() -> argparse.Namespace:
    """Parse and validate command-line arguments"""
    parser = argparse.ArgumentParser(description="Justifactu")
    ONEDRIVE_DATA_FOLDER = ROOT_FOLDER / "service/onedrive/data"
    SHAREPOINT_SYNC_FOLDER = "justifactu/runtime"

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
        "--onedrive_data_folder",
        type=parse_directory,
        required=False,
        default=ONEDRIVE_DATA_FOLDER,
        help="Location for all Onedrive data on local.",
    )

    parser.add_argument(
        "--onedrive_conf_folder",
        type=parse_directory,
        required=False,
        default=ROOT_FOLDER / "service/onedrive/conf",
        help="Location for all Onedrive configuration on local.",
    )

    parser.add_argument(
        "--onedrive_logs_folder",
        type=parse_directory,
        required=False,
        default=ROOT_FOLDER / "service/onedrive/logs",
        help="Location for all Onedrive logs on local.",
    )

    parser.add_argument(
        "--sharepoint_sync_folder",
        type=parse_directory,
        required=False,
        default=Path(SHAREPOINT_SYNC_FOLDER),
        help="Location for all SharePoint synced data on local.",
    )

    parser.add_argument(
        "--runtime_location",
        type=parse_directory,
        required=False,
        default=None,
    )

    parser.add_argument(
        "--download-input",
        action="store_true",
        default=False,
        help="Force a fresh download of the input folder from SharePoint before processing, "
        "as a fallback if OneDrive-for-Linux sync has failed or fallen behind. "
        "Only meaningful with --location sharepoint.",
    )

    parser.add_argument(
        "-p",
        "--phase",
        type=parse_phase,
        required=False,
        default=None,
        help="Which phase to run. Possible values: "
        + ", ".join(p.value for p in Phase),
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

    if args.runtime_location is None:
        args.runtime_location = args.onedrive_data_folder / args.sharepoint_sync_folder

    return args
