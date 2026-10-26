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
import os
from pathlib import Path

from justifactu.custom_except import ArgumentInputLocationError
from justifactu.defines import InputLocation, Phase, Mode
from justifactu.defaults import (
    default_onedrive_data_folder,
    default_onedrive_conf_folder,
)
from justifactu.paths import sharepoint_sync_folder


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


def parse_mode(value: str) -> Mode:
    try:
        return Mode(value)
    except ValueError:
        raise ArgumentInputLocationError(
            'The mode supplied "' + value + '" is not defined.'
        )


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
        "--auth",
        action="store_true",
        default=False,
        help="Runs the program once to authenticate with the OneDrive API, then exits.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview pending changes without applying them.",
    )

    parser.add_argument(
        "--onedrive-data-folder",
        type=parse_directory,
        required=False,
        default=Path(os.environ.get("OD_DATA", str(default_onedrive_data_folder()))),
        help="Location for all Onedrive data on local.",
    )

    parser.add_argument(
        "--onedrive-conf-folder",
        type=parse_directory,
        required=False,
        default=Path(os.environ.get("OD_CONF", str(default_onedrive_conf_folder()))),
        help="Location for all Onedrive configuration on local.",
    )

    parser.add_argument(
        "--sharepoint-sync-folder",
        type=parse_directory,
        required=False,
        default=None,
        help="Location for all SharePoint synced data on local.",
    )

    parser.add_argument(
        "--runtime-location",
        type=parse_directory,
        required=False,
        default=None,
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

    parser.add_argument(
        "--mode",
        type=parse_mode,
        required=False,
        default=Mode.TEST,
        help="Run mode. Possible values: " + ", ".join(m.value for m in Mode),
    )

    parser.add_argument(
        "--ledger-path",
        type=parse_file,
        required=False,
        default=None,
        help="Path to the bank statement reconciliation ledger (.xlsx) mapping "
        "transaction dates/totals to SAP IDs. Required when running phase 1 "
        "or a full run (no --phase given).",
    )

    args = parser.parse_args()
    return args


def parse_file(value: str) -> Path:
    path = Path(value)
    if not path.exists():
        raise ArgumentInputLocationError(f"Path {value} does not exist")
    if not path.is_file():
        raise ArgumentInputLocationError(f"Path {value} is not a file")
    return path


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

        if args.sharepoint_sync_folder is None:
            args.sharepoint_sync_folder = parse_directory(
                str(sharepoint_sync_folder(args.mode))
            )

        if args.runtime_location is None:
            args.runtime_location = parse_directory(
                str(args.onedrive_data_folder / args.sharepoint_sync_folder)
            )

        phase_needs_ledger = args.phase in (None, Phase.PHASE_1)
        if phase_needs_ledger and args.ledger_path is None:
            raise ArgumentInputLocationError(
                "--ledger-path is required when running phase 1 or a full run "
                "(no --phase specified)."
            )

    except (argparse.ArgumentTypeError, ArgumentInputLocationError) as e:
        print("Arguments couldn't be parsed. Internal error is " + str(e))
        print(common)
        exit(5)

    return args
