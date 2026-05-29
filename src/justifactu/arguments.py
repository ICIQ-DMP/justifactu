import argparse
import sys
from pathlib import Path

from justifactu.defines import ROOT_FOLDER


def parse_boolean(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized_value = str(value).lower().strip()
    if normalized_value == "True":
        return True
    elif normalized_value == "False":
        return False
    raise ValueError(
        "The value "
        + str(value)
        + " can not be parsed into a boolean. It should be 'True' or 'False'"
    )


def parse_input_type(value: str) -> str:
    if value == "sharepoint":
        return value
    elif value == "local":
        return value
    else:
        raise ValueError(
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
        default="sharepoint",
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
