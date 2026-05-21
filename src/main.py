import os.path
import os.path
import os.path
import shutil
from datetime import datetime
from pathlib import Path

from arguments import process_parse_arguments
from pdf import parse_sap_id_from_bill
from src.filesystem import list_dir

logger = None


def compute_path(partial_path, extension):
    suffix = 1
    output_path = partial_path + extension
    while os.path.exists(output_path):
        if suffix < 100:
            str_suffix = "00" + str(suffix)
        elif suffix < 10:
            str_suffix = "0" + str(suffix)
        else:
            str_suffix = str(suffix)
        output_path = partial_path + "_" + str_suffix + extension
        suffix += 1

    return output_path


def datetime_range(begin, end):
    current = datetime(begin.year, begin.month, 1)

    result = []
    while current <= end:
        result.append(datetime.strptime(str(current.year * 100 + current.month), "%Y%m"))
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    return result


def reverse_dict(d: dict):
    r = {}
    for key in d.keys():
        r[d[key]] = key
    return r


def main():
    args = process_parse_arguments()

    if args.input_location:
        INPUT_FOLDER = args.input_location
    else:
        INPUT_FOLDER = Path("./service/onedrive/data/Justificació Projectes/Automatització Vinculacio Pagaments/_input")

    REMESES_FOLDER = os.path.join(INPUT_FOLDER, "Remeses")

    REMESA_BBVA_FOLDER_NAME = "Remesa BBVA"
    REMESA_SABADELL_FOLDER_NAME = "Remesa Sabadell"

    REMESES_FOLDER_NAMES = []
    REMESES_FOLDER_NAMES.append(REMESA_BBVA_FOLDER_NAME)
    REMESES_FOLDER_NAMES.append(REMESA_SABADELL_FOLDER_NAME)

    REMESA_PER_YEAR_PREFIX = "Remesa "
    NOW = datetime.now()
    years_to_process = []
    years_to_process.append(NOW.year)
    if NOW.month <= 3:
        years_to_process.append(NOW.year - 1)
    years_to_process.remove(2026)  # TODO: temporal for making tests

    folders_to_process = []
    for year in years_to_process:
        for remesa_folder_names in REMESES_FOLDER_NAMES:
            folders_to_process.append(os.path.join(REMESES_FOLDER, REMESA_PER_YEAR_PREFIX + str(year), remesa_folder_names))

    for folder in folders_to_process:
        remesa_folders = list_dir(folder)
        for remesa_folder in remesa_folders:
            for file in list_dir(os.path.join(folder, remesa_folder)):
                if file.endswith(".xls") or file.endswith(".xlsx"):
                    continue
                bill_id = parse_sap_id_from_bill(os.path.join(folder, remesa_folder, file))
                source = os.path.join(folder, remesa_folder, file)
                print(folder)
                print(remesa_folder)
                print(bill_id)
                print(file)
                dest = os.path.join(folder, remesa_folder, bill_id)
                shutil.move(source, dest)



    print(f"input folder is {INPUT_FOLDER}")
    print("Justifactu process is finished.")
    print("Sending notification email")


if __name__ == "__main__":
    main()
