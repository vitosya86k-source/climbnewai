"""Конфигурация приложения"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Базовые пути
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
TEMP_DIR = DATA_DIR / "temp"
EXPORTS_DIR = DATA_DIR / "exports"
BOLDERING_DIR = DATA_DIR / "boldering_vector"

# Создание директорий
TEMP_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
BOLDERING_DIR.mkdir(parents=True, exist_ok=True)

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# BoulderVision настройки
BOULDERVISION_BUFFER_SIZE = int(os.getenv("BOULDERVISION_BUFFER_SIZE", "60"))  # Кадров в буфере

MAX_VIDEO_SIZE_MB = int(os.getenv("MAX_VIDEO_SIZE_MB", "100"))
MAX_VIDEO_DURATION_SEC = int(os.getenv("MAX_VIDEO_DURATION_SEC", "120"))
# Таймаут загрузки видео/фото в Telegram (сек). Библиотека по умолчанию даёт 20 с — мало для больших файлов.
MEDIA_UPLOAD_TIMEOUT = float(os.getenv("MEDIA_UPLOAD_TIMEOUT", "1200"))

# Video Processing
MEDIAPIPE_MODEL_COMPLEXITY = int(os.getenv("MEDIAPIPE_MODEL_COMPLEXITY", "2"))
FRAME_SKIP = int(os.getenv("FRAME_SKIP", "1"))

# Concurrency
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "2"))

# Railway
PORT = int(os.getenv("PORT", "8080"))

# Validation
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен!")

# Версия без ИИ: отчёты генерируются только алгоритмически
