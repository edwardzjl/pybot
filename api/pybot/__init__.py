import sys

from loguru import logger

from pybot.config import settings
from pybot.main import app

__all__ = ["app"]

logger.remove()
logger.add(sys.stdout, level=settings.log_level)
