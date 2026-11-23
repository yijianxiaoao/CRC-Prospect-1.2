# -*- coding: utf-8 -*-
"""Unified logging utility: console + rotating file logs. """
import logging
import os
from logging.handlers import RotatingFileHandler

_FORMAT = '%(asctime)s [%(levelname)s] %(name)s - %(message)s'
_configured = False
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'data', 'logs')


def _ensure() -> None:
    global _configured
    if _configured:
        return
    formatter = logging.Formatter(_FORMAT)
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
               for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)

    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        log_path = os.path.join(LOG_DIR, 'app.log')
        if not any(isinstance(h, RotatingFileHandler) and
                   getattr(h, 'baseFilename', '') == os.path.abspath(log_path)
                   for h in root.handlers):
            file_handler = RotatingFileHandler(
                log_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8')
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
    except OSError:
        logging.getLogger(__name__).warning('Unable to create log directory: %s', LOG_DIR)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return the centrally configured logger. """
    _ensure()
    return logging.getLogger(name)
