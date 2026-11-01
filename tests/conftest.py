"""Shared test configuration: never write log files during test runs."""

import os

os.environ.setdefault("TRADING_BOT_LOG_FILE", "0")
