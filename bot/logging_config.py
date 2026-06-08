import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "trading_bot.log"
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3
FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

_setup_complete = False


def setup_logging() -> None:
    global _setup_complete
    if _setup_complete:
        return

    LOG_DIR.mkdir(exist_ok=True)

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(FILE_FORMAT))

    console_handler = RichHandler(
        show_time=True, show_path=False, markup=True, rich_tracebacks=True
    )
    console_handler.setLevel(logging.INFO)

    root = logging.getLogger("bot")
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _setup_complete = True
