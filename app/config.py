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

# Claude API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Roboflow API (для BoulderVision детекции зацепов)
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")
ROBOFLOW_PROJECT = os.getenv("ROBOFLOW_PROJECT", "climbing-route-1-hold-detection")
ROBOFLOW_MODEL_VERSION = int(os.getenv("ROBOFLOW_MODEL_VERSION", "1"))

# Масса спортсмена (кг) для расчёта нагрузок (если задана)
MASS_KG = float(os.getenv("MASS_KG", "0"))  # 0 = не задан

# BoulderVision настройки
BOULDERVISION_BUFFER_SIZE = int(os.getenv("BOULDERVISION_BUFFER_SIZE", "60"))  # Кадров в буфере
BOULDERVISION_HOLD_THRESHOLD = float(os.getenv("BOULDERVISION_HOLD_THRESHOLD", "0.1"))  # Порог сопоставления
ENABLE_HOLD_DETECTION = os.getenv("ENABLE_HOLD_DETECTION", "false").lower() == "true"

# Database
DEV_MODE = os.getenv("DEV_MODE", "True").lower() == "true"
if DEV_MODE:
    DATABASE_URL = os.getenv("DEV_DATABASE_URL", "sqlite:///./climbai.db")
else:
    DATABASE_URL = os.getenv("DATABASE_URL")

# Limits
FREE_VIDEO_LIMIT = int(os.getenv("FREE_VIDEO_LIMIT", "3"))
MAX_VIDEO_SIZE_MB = int(os.getenv("MAX_VIDEO_SIZE_MB", "100"))
MAX_VIDEO_DURATION_SEC = int(os.getenv("MAX_VIDEO_DURATION_SEC", "120"))
# Таймаут загрузки видео/фото в Telegram (сек). Библиотека по умолчанию даёт 20 с — мало для больших файлов.
MEDIA_UPLOAD_TIMEOUT = float(os.getenv("MEDIA_UPLOAD_TIMEOUT", "1200"))

# Video Processing
MEDIAPIPE_MODEL_COMPLEXITY = int(os.getenv("MEDIAPIPE_MODEL_COMPLEXITY", "2"))
FRAME_SKIP = int(os.getenv("FRAME_SKIP", "1"))

# Railway
PORT = int(os.getenv("PORT", "8080"))

# Validation
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен!")

# ANTHROPIC_API_KEY опционален: без него отчёты идут через fallback (без ИИ)


