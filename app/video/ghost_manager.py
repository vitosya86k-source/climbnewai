"""
Ghost Manager - Управление эталонными видео v1.0

Позволяет:
- Извлекать landmarks из эталонного видео
- Сохранять/загружать эталоны в JSON
- Сравнивать текущее видео с эталоном
- Использовать лучшую попытку как эталон
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import cv2
import mediapipe as mp
import numpy as np

from app.config import DATA_DIR, MEDIAPIPE_MODEL_COMPLEXITY

logger = logging.getLogger(__name__)

# Директория для хранения эталонов
GHOSTS_DIR = DATA_DIR / "ghosts"
GHOSTS_DIR.mkdir(parents=True, exist_ok=True)


class GhostManager:
    """
    Менеджер эталонных видео (призраков)

    Позволяет создавать, сохранять и загружать эталонные
    последовательности landmarks для сравнения.
    """

    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=MEDIAPIPE_MODEL_COMPLEXITY,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def extract_landmarks_from_video(
        self,
        video_path: Path,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Извлекает последовательность landmarks из видео

        Args:
            video_path: путь к видео
            progress_callback: функция обратного вызова для прогресса

        Returns:
            list: последовательность landmarks по кадрам
        """
        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            raise ValueError(f"Не удалось открыть видео: {video_path}")

        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info(f"Извлечение landmarks из {video_path}: {total_frames} кадров")

        landmarks_sequence = []
        frame_number = 0

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Конвертируем в RGB для MediaPipe
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.pose.process(frame_rgb)

                # Сохраняем landmarks
                frame_landmarks = None
                if results.pose_landmarks:
                    frame_landmarks = self._landmarks_to_dict(results.pose_landmarks)

                landmarks_sequence.append({
                    'frame': frame_number,
                    'timestamp': frame_number / fps if fps > 0 else 0,
                    'landmarks': frame_landmarks
                })

                # Прогресс
                if progress_callback and frame_number % 30 == 0:
                    progress = int((frame_number / total_frames) * 100)
                    progress_callback(progress)

                frame_number += 1

        finally:
            cap.release()

        logger.info(f"Извлечено {len(landmarks_sequence)} кадров с landmarks")

        return landmarks_sequence

    def _landmarks_to_dict(self, landmarks) -> List[Dict[str, float]]:
        """Конвертирует MediaPipe landmarks в словарь"""
        result = []
        for lm in landmarks.landmark:
            result.append({
                'x': lm.x,
                'y': lm.y,
                'z': lm.z,
                'visibility': lm.visibility
            })
        return result

    def save_ghost(
        self,
        landmarks_sequence: List[Dict[str, Any]],
        name: str,
        metadata: Dict[str, Any] = None
    ) -> Path:
        """
        Сохраняет эталон в файл

        Args:
            landmarks_sequence: последовательность landmarks
            name: название эталона (будет использовано как имя файла)
            metadata: дополнительная информация (описание, автор и т.д.)

        Returns:
            Path: путь к сохранённому файлу
        """
        # Очищаем имя от недопустимых символов
        safe_name = "".join(c for c in name if c.isalnum() or c in "._- ")
        safe_name = safe_name.strip().replace(" ", "_")

        ghost_file = GHOSTS_DIR / f"{safe_name}.json"

        ghost_data = {
            'name': name,
            'metadata': metadata or {},
            'total_frames': len(landmarks_sequence),
            'landmarks': landmarks_sequence
        }

        with open(ghost_file, 'w', encoding='utf-8') as f:
            json.dump(ghost_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Эталон сохранён: {ghost_file}")
        return ghost_file

    def load_ghost(self, name_or_path: str) -> Optional[Dict[str, Any]]:
        """
        Загружает эталон из файла

        Args:
            name_or_path: название эталона или путь к файлу

        Returns:
            dict: данные эталона или None если не найден
        """
        # Определяем путь
        if Path(name_or_path).exists():
            ghost_file = Path(name_or_path)
        else:
            safe_name = "".join(c for c in name_or_path if c.isalnum() or c in "._- ")
            safe_name = safe_name.strip().replace(" ", "_")
            ghost_file = GHOSTS_DIR / f"{safe_name}.json"

        if not ghost_file.exists():
            logger.warning(f"Эталон не найден: {ghost_file}")
            return None

        try:
            with open(ghost_file, 'r', encoding='utf-8') as f:
                ghost_data = json.load(f)

            logger.info(f"Эталон загружен: {ghost_data['name']}, {ghost_data['total_frames']} кадров")
            return ghost_data

        except Exception as e:
            logger.error(f"Ошибка загрузки эталона: {e}")
            return None

    def list_ghosts(self) -> List[Dict[str, Any]]:
        """
        Возвращает список доступных эталонов

        Returns:
            list: список с информацией об эталонах
        """
        ghosts = []

        for ghost_file in GHOSTS_DIR.glob("*.json"):
            try:
                with open(ghost_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    ghosts.append({
                        'name': data.get('name', ghost_file.stem),
                        'file': str(ghost_file),
                        'total_frames': data.get('total_frames', 0),
                        'metadata': data.get('metadata', {})
                    })
            except Exception as e:
                logger.warning(f"Не удалось прочитать {ghost_file}: {e}")

        return ghosts

    def delete_ghost(self, name: str) -> bool:
        """Удаляет эталон"""
        safe_name = "".join(c for c in name if c.isalnum() or c in "._- ")
        safe_name = safe_name.strip().replace(" ", "_")
        ghost_file = GHOSTS_DIR / f"{safe_name}.json"

        if ghost_file.exists():
            ghost_file.unlink()
            logger.info(f"Эталон удалён: {name}")
            return True
        return False

    def get_landmarks_for_overlay(self, ghost_data: Dict[str, Any]) -> List[List[Dict]]:
        """
        Извлекает landmarks в формате для VideoOverlays

        Args:
            ghost_data: загруженные данные эталона

        Returns:
            list: список landmarks по кадрам
        """
        landmarks_list = []

        for frame_data in ghost_data.get('landmarks', []):
            landmarks = frame_data.get('landmarks')
            if landmarks:
                landmarks_list.append(landmarks)
            else:
                # Если нет landmarks для кадра, добавляем пустой
                landmarks_list.append(None)

        return landmarks_list

    def create_ghost_from_current_video(
        self,
        video_path: Path,
        name: str,
        description: str = ""
    ) -> Path:
        """
        Создаёт эталон из текущего видео (лучшая попытка)

        Args:
            video_path: путь к видео
            name: название эталона
            description: описание

        Returns:
            Path: путь к сохранённому эталону
        """
        # Извлекаем landmarks
        landmarks_sequence = self.extract_landmarks_from_video(video_path)

        # Сохраняем
        metadata = {
            'description': description,
            'source': str(video_path),
            'type': 'user_best'
        }

        return self.save_ghost(landmarks_sequence, name, metadata)

    def calculate_similarity(
        self,
        current_landmarks: List[Dict],
        ghost_landmarks: List[Dict],
        frame_offset: int = 0
    ) -> float:
        """
        Рассчитывает схожесть текущих landmarks с эталоном

        Args:
            current_landmarks: текущие landmarks (dict формат)
            ghost_landmarks: эталонные landmarks
            frame_offset: смещение кадров (для синхронизации)

        Returns:
            float: коэффициент схожести (0-100)
        """
        if not current_landmarks or not ghost_landmarks:
            return 0.0

        total_diff = 0
        count = 0

        # Ключевые точки для сравнения (верхняя часть тела)
        key_points = [11, 12, 13, 14, 15, 16, 23, 24]  # Плечи, локти, запястья, бёдра

        for idx in key_points:
            if idx < len(current_landmarks) and idx < len(ghost_landmarks):
                curr = current_landmarks[idx]
                ghost = ghost_landmarks[idx]

                if curr and ghost:
                    # Евклидово расстояние
                    dx = curr.get('x', 0) - ghost.get('x', 0)
                    dy = curr.get('y', 0) - ghost.get('y', 0)
                    diff = np.sqrt(dx**2 + dy**2)
                    total_diff += diff
                    count += 1

        if count == 0:
            return 0.0

        avg_diff = total_diff / count

        # Конвертируем в проценты (0% = очень разные, 100% = идентичные)
        # Максимальное расстояние примерно 1.4 (диагональ квадрата 1x1)
        similarity = max(0, 100 * (1 - avg_diff / 0.5))

        return min(100, similarity)


# Глобальный экземпляр для удобства
ghost_manager = GhostManager()


def create_ghost_from_video(video_path: str, name: str, description: str = "") -> str:
    """Утилитарная функция для создания эталона"""
    path = ghost_manager.create_ghost_from_current_video(
        Path(video_path), name, description
    )
    return str(path)


def load_ghost_for_overlay(name: str) -> Optional[List]:
    """Утилитарная функция для загрузки эталона"""
    ghost_data = ghost_manager.load_ghost(name)
    if ghost_data:
        return ghost_manager.get_landmarks_for_overlay(ghost_data)
    return None


def list_available_ghosts() -> List[Dict]:
    """Утилитарная функция для получения списка эталонов"""
    return ghost_manager.list_ghosts()
