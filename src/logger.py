import logging
from enum import Enum
from pathlib import Path
from typing import Optional, Any, cast
from rich.logging import RichHandler
from src.defines import ROOT_FOLDER, NOW

# ---- extend the logging module with TRACE
DATE_FORMAT = "%d/%m/%Y"
TRACE_LEVEL_NUM = 1
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")
MESSAGE_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
GENERAL_OUTPUT_FOLDER: Path = ROOT_FOLDER / "output"
ADMIN_LOG_FOLDER: Path = GENERAL_OUTPUT_FOLDER / "_admin_logs"


class LogLevel(str, Enum):
    """
    Logical log levels for the CLI.

    Includes a custom TRACE (more verbose than DEBUG) and QUIET
    (suppresses all output beyond CRITICAL).
    """

    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    QUIET = "quiet"

    @classmethod
    def parse(cls, value: Optional[str]) -> Optional["LogLevel"]:
        """Parse case-insensitively; returns None if value is falsy."""
        print("Executing function parse from LogLevel")
        if not value:
            return None
        norm = value.strip().lower()
        try:
            return cls(norm)
        except ValueError as exc:
            valid = ", ".join(v.value for v in cls)
            raise ValueError(f"Unknown log level '{value}'. Valid: {valid}") from exc

    @classmethod
    def get_default_log_level(cls) -> "LogLevel":
        return LogLevel.TRACE

    def to_logging_level(self) -> int:
        if self is LogLevel.TRACE:
            return 0
        if self is LogLevel.DEBUG:
            return logging.DEBUG
        if self is LogLevel.INFO:
            return logging.INFO
        if self is LogLevel.WARNING:
            return logging.WARNING
        if self is LogLevel.ERROR:
            return logging.ERROR
        if self is LogLevel.QUIET:
            return logging.CRITICAL + 10
        return LogLevel.get_default_log_level().to_logging_level()


def get_default_log_path() -> Path:
    return ADMIN_LOG_FOLDER / (NOW + ".log")


def get_supervisor_log_path() -> Path:
    return get_default_log_path()


def get_user_log_path() -> Path:
    return get_default_log_path()


class ExtendedLogger(logging.Logger):
    def trace(self: logging.Logger, message: str, *args: Any, **kwargs: Any) -> None:
        self._log(TRACE_LEVEL_NUM, message, args, **kwargs)


# Tell the logging system to use your new class
logging.setLoggerClass(ExtendedLogger)


class SecretsFilter(logging.Filter):
    def __init__(self, secrets: list[str] | None):
        super().__init__()
        self.secrets: list[str] = secrets or []

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.secrets:
            return True

        if isinstance(record.msg, str):
            for secret in self.secrets:
                if secret and secret in record.msg:
                    record.msg = record.msg.replace(secret, "*****")

        return True


def setup_logging(
    level: Optional[int | None] = None,
    user_report_file: Optional[str | Path] = None,
    admin_log_file: Optional[str | Path] = None,
    supervisor_log_file: Optional[str | Path] = None,
    secrets: list[str] | None = None,
) -> None:
    # Default level is DEBUG
    if level is None:
        level = LogLevel.get_default_log_level().to_logging_level()

    handlers: list[logging.Handler] = []
    secrets_filter = SecretsFilter(secrets)

    # ---- console (Rich)
    console = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_time=False,
        show_level=True,
        show_path=False,
    )
    common_formatter = logging.Formatter(MESSAGE_FORMAT, DATE_FORMAT)
    console.setLevel(level)
    console.setFormatter(common_formatter)
    console.addFilter(secrets_filter)
    handlers.append(console)

    log_files = [
        (user_report_file, level),
        (admin_log_file, logging.ERROR),
        (supervisor_log_file, logging.WARNING),
    ]

    for log_file_i in log_files:
        if log_file_i[0]:
            path = Path(log_file_i[0])
            path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(path, encoding="utf-8")
            file_handler.setFormatter(common_formatter)
            file_handler.addFilter(secrets_filter)
            file_handler.setLevel(log_file_i[1])
            handlers.append(file_handler)

    logging.basicConfig(
        level=level,  # root captures everything
        handlers=handlers,
        format=MESSAGE_FORMAT,
        force=True,
    )


def obfuscate_text(text: str | None) -> str:
    if text is None:
        return str(text)
    else:
        return "*****"


def get_logger(name: str) -> ExtendedLogger:
    """Return a logger with trace() method available."""
    return cast(ExtendedLogger, logging.getLogger(name))


def process_log_flags(
    very_verbose: bool, verbose: bool, quiet: bool, very_quiet: bool
) -> tuple[LogLevel | None, bool]:
    more_than_one_flag = False
    flag_counter = 0
    for flag in (very_verbose, verbose, quiet, very_quiet):
        if flag:
            flag_counter += 1
    if flag_counter > 1:
        more_than_one_flag = True

    if very_verbose:
        return LogLevel.TRACE, more_than_one_flag
    elif verbose:
        return LogLevel.DEBUG, more_than_one_flag
    elif quiet:
        return LogLevel.WARNING, more_than_one_flag
    elif very_quiet:
        return LogLevel.QUIET, more_than_one_flag
    else:
        return None, more_than_one_flag


def configure_logging_from_settings(
    level: Optional[LogLevel] = None,
    user_report_file: Optional[str | Path] = None,
    admin_log_file: Optional[str | Path] = None,
    supervisor_log_file: Optional[str | Path] = None,
    secrets: Optional[list[str]] = None,
) -> None:

    if user_report_file is None:
        user_report_file = get_default_log_path()
    if admin_log_file is None:
        admin_log_file = get_default_log_path()
    if supervisor_log_file is None:
        supervisor_log_file = get_default_log_path()

    if level is None:
        level = LogLevel.get_default_log_level()

    setup_logging(
        level=level.to_logging_level(),
        user_report_file=user_report_file,
        admin_log_file=admin_log_file,
        supervisor_log_file=supervisor_log_file,
        secrets=secrets,
    )  # Preventive creation of log for logging the loading of settings
