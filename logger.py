"""
logger.py — Sistema de logging centralizado da Kuri.

Substitui todos os print() dispersos por logs estruturados.
- Console: formato colorido compacto.
- Arquivo: kuri.log com rotação (5MB max, 3 backups).
"""

import logging
import sys
from logging.handlers import RotatingFileHandler

LOG_FILE = "kuri.log"
LOG_FORMAT = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger nomeado configurado para console + arquivo rotativo.

    Usage:
        from logger import get_logger
        log = get_logger("brain")
        log.info("Kuri pensando...")
    """
    logger = logging.getLogger(name)

    # Evita handlers duplicados se chamado mais de uma vez para o mesmo nome
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (com rotação)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        # Se não conseguir criar o arquivo de log, segue só com console
        logger.warning(
            "Não foi possível criar o arquivo de log. Usando apenas console."
        )

    return logger
