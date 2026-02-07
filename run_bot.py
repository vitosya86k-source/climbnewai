"""Вспомогательный скрипт для запуска бота"""
import sys
from pathlib import Path

# Добавляем путь
sys.path.insert(0, str(Path(__file__).parent))

# Запускаем
from app.main import main

if __name__ == "__main__":
    main()

