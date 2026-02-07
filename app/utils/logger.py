"""Настройка логирования"""

import logging
import sys
from pathlib import Path


def setup_logger(name: str = "climbai", level: int = logging.INFO) -> logging.Logger:
    """Настраивает и возвращает logger"""
    
    # Создаем logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Избегаем дублирования handlers
    if logger.handlers:
        return logger
    
    # Формат
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (опционально)
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    file_handler = logging.FileHandler(log_dir / "climbai.log", encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


