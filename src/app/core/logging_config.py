import logging
import sys
from pythonjsonlogger.json import JsonFormatter
from app.core.config import settings


class RAGJsonFormatter(JsonFormatter):
    """Adds default fields to every log record."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict) # parent does its work first
        log_record["service"] = "rag-from-scratch" # add custom fields
        log_record["level"] = record.levelname

    
def setup_logging() -> logging.Logger:
    logger = logging.getLogger("rag")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler - outputs json to stdout
    handler = logging.StreamHandler(sys.stdout)
    formatter = RAGJsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger

logger = setup_logging()
