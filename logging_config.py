from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    root.addHandler(console)

    log_dir = os.environ.get("LOG_DIR", "logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
        app_path = os.path.join(log_dir, "app.log")
        err_path = os.path.join(log_dir, "errors.log")

        app_handler = RotatingFileHandler(
            app_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        app_handler.setLevel(logging.INFO)
        app_handler.setFormatter(fmt)

        err_handler = RotatingFileHandler(
            err_path, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        err_handler.setLevel(logging.ERROR)
        err_handler.setFormatter(fmt)

        root.addHandler(app_handler)
        root.addHandler(err_handler)
    except OSError as e:
        root.warning("File logging disabled (%s), using console only", e)
