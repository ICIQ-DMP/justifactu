import os
from pathlib import Path
from typing import List


def list_dir(input_folder: Path) -> List[Path]:
    """Returns a list of all file names in the ./input/salaries directory."""
    # Ensure the input_folder is a valid directory
    if not os.path.isdir(input_folder):
        raise ValueError(
            "input folder "
            + str(input_folder)
            + " in list_files function is not a directory or can't be accessed"
        )

    # List all files in the directory
    file_names = []
    for file_name in input_folder.iterdir():
        file_names.append(file_name)

    return file_names
