"""
Валидация видеофайлов для защиты от DoS атак и битых файлов
"""

import cv2
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

# Поддерживаемые форматы (расширения)
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}

# Минимальные требования к видео
MIN_WIDTH = 320
MIN_HEIGHT = 240
MIN_FPS = 10
MAX_FPS = 120


def validate_video_file(video_path: Path) -> Tuple[bool, str]:
    """
    Валидация видеофайла перед обработкой
    
    Проверяет:
    - Существование файла
    - Формат файла
    - Корректность видео (можно ли открыть)
    - Минимальные характеристики (разрешение, FPS)
    - Наличие читаемых кадров
    
    Args:
        video_path: путь к видеофайлу
        
    Returns:
        (is_valid, error_message): True если валидный, иначе False с описанием ошибки
    """
    try:
        # 1. Проверка существования файла
        if not video_path.exists():
            return False, "Файл не найден"
        
        if not video_path.is_file():
            return False, "Указанный путь не является файлом"
        
        # 2. Проверка расширения файла
        file_ext = video_path.suffix.lower()
        if file_ext not in ALLOWED_VIDEO_EXTENSIONS:
            return False, f"Неподдерживаемый формат: {file_ext}. Допустимые: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        
        # 3. Попытка открыть видео через OpenCV
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            return False, "Не удалось открыть видеофайл (возможно, файл поврежден)"
        
        try:
            # 4. Получение метаданных
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 5. Проверка минимальных характеристик
            if width < MIN_WIDTH or height < MIN_HEIGHT:
                return False, f"Разрешение слишком низкое: {width}x{height} (минимум {MIN_WIDTH}x{MIN_HEIGHT})"
            
            if fps <= 0 or fps < MIN_FPS:
                return False, f"Некорректный FPS: {fps} (минимум {MIN_FPS})"
            
            if fps > MAX_FPS:
                return False, f"Слишком высокий FPS: {fps} (максимум {MAX_FPS})"
            
            if frame_count <= 0:
                return False, "Видео не содержит кадров"
            
            # 6. Попытка прочитать несколько кадров для проверки читаемости
            readable_frames = 0
            test_frames = min(5, frame_count)  # Проверяем первые 5 кадров или меньше
            
            for i in range(test_frames):
                ret, frame = cap.read()
                if ret and frame is not None:
                    # Проверяем, что кадр не пустой
                    if frame.size > 0:
                        readable_frames += 1
                else:
                    break
            
            if readable_frames == 0:
                return False, "Не удалось прочитать ни одного кадра из видео"
            
            # Предупреждение если не все кадры читаются (но не критично)
            if readable_frames < test_frames:
                logger.warning(f"Прочитано только {readable_frames}/{test_frames} тестовых кадров")
            
            logger.info(f"Видео валидно: {width}x{height}, {fps:.1f} FPS, {frame_count} кадров")
            return True, "OK"
            
        finally:
            # Обязательно освобождаем ресурсы
            cap.release()
    
    except Exception as e:
        logger.error(f"Ошибка при валидации видео: {e}", exc_info=True)
        return False, f"Ошибка валидации: {str(e)}"


def get_video_info(video_path: Path) -> dict:
    """
    Получить информацию о видеофайле
    
    Args:
        video_path: путь к видеофайлу
        
    Returns:
        dict с информацией о видео или пустой dict при ошибке
    """
    try:
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            return {}
        
        try:
            info = {
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': cap.get(cv2.CAP_PROP_FPS),
                'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                'duration': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS) if cap.get(cv2.CAP_PROP_FPS) > 0 else 0
            }
            return info
        finally:
            cap.release()
    
    except Exception as e:
        logger.error(f"Ошибка при получении информации о видео: {e}")
        return {}
