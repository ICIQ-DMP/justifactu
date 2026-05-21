import datetime
from pathlib import Path

ROOT_FOLDER: Path = Path(__file__).resolve().parent.parent
PROJECT_DIR: Path = ROOT_FOLDER  # alias kept for compatibility

DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
NOW_DATA = datetime.datetime.now()
NOW = NOW_DATA.strftime(DATETIME_FORMAT)