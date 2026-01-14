import logging
import logging.handlers
from pathlib import Path

from valutatrade_hub.core.settings import settings


def setup_logging():
    """Настраивает систему логирования"""
    log_path = settings.get("log_path")
    
    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("valutatrade_hub")
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        return logger
    

    formatter = logging.Formatter(
        '%(levelname)s %(asctime)s %(message)s',
        datefmt="%Y-%m-%dT%H:%M:%S"
    )
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name=None):
    """Получает логгер для указанного модуля"""
    if name:
        return logging.getLogger(f"valutatrade_hub.{name}")
    return logging.getLogger("valutatrade_hub")


setup_logging()
