"""
Детектор зацепов через Roboflow API

Основано на: https://github.com/reiffd7/BoulderVision
Документация: https://blog.roboflow.com/bouldering/

Функционал:
- Детекция зацепов на изображении/видео
- Классификация цвета зацепов
- Сопоставление руки/ноги с ближайшим зацепом
- Анализ времени на каждом зацепе
"""

import os
import cv2
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

# Попытка импорта Roboflow
try:
    from roboflow import Roboflow
    ROBOFLOW_AVAILABLE = True
except ImportError:
    ROBOFLOW_AVAILABLE = False
    logger.warning("Roboflow не установлен. Детекция зацепов будет недоступна.")


@dataclass
class Hold:
    """Представление зацепа"""
    id: int
    x: float           # Центр X (0-1 нормализовано)
    y: float           # Центр Y (0-1 нормализовано)
    width: float       # Ширина (0-1)
    height: float      # Высота (0-1)
    confidence: float  # Уверенность детекции
    color: str         # Цвет зацепа
    class_name: str    # Класс от модели
    
    def get_bbox_pixels(self, frame_width: int, frame_height: int) -> Tuple[int, int, int, int]:
        """Возвращает bbox в пикселях (x1, y1, x2, y2)"""
        x1 = int((self.x - self.width/2) * frame_width)
        y1 = int((self.y - self.height/2) * frame_height)
        x2 = int((self.x + self.width/2) * frame_width)
        y2 = int((self.y + self.height/2) * frame_height)
        return (x1, y1, x2, y2)
    
    def get_center_pixels(self, frame_width: int, frame_height: int) -> Tuple[int, int]:
        """Возвращает центр в пикселях"""
        return (int(self.x * frame_width), int(self.y * frame_height))


@dataclass
class HoldInteraction:
    """Взаимодействие конечности с зацепом"""
    hold_id: int
    limb: str          # 'left_hand', 'right_hand', 'left_foot', 'right_foot'
    start_frame: int
    end_frame: Optional[int] = None
    duration_frames: int = 0
    hold_color: str = ""


class HoldsDetector:
    """
    Детектор зацепов с использованием Roboflow API
    
    Использует двухэтапный подход из BoulderVision:
    1. YOLO детекция зацепов
    2. Классификация цвета
    """
    
    # Цвета для визуализации
    HOLD_COLORS = {
        'red': (0, 0, 255),
        'blue': (255, 0, 0),
        'green': (0, 255, 0),
        'yellow': (0, 255, 255),
        'orange': (0, 165, 255),
        'pink': (203, 192, 255),
        'purple': (128, 0, 128),
        'white': (255, 255, 255),
        'black': (50, 50, 50),
        'unknown': (128, 128, 128)
    }
    
    # Маппинг конечностей к индексам MediaPipe
    LIMB_KEYPOINTS = {
        'left_hand': 15,   # left_wrist
        'right_hand': 16,  # right_wrist
        'left_foot': 27,   # left_ankle
        'right_foot': 28   # right_ankle
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        project_name: str = "climbing-holds",
        model_version: int = 1,
        confidence_threshold: float = 0.3,
        enable_color_classification: bool = True
    ):
        """
        Args:
            api_key: Roboflow API ключ (если None, берется из env)
            project_name: Название проекта на Roboflow
            model_version: Версия модели
            confidence_threshold: Порог уверенности для детекции
            enable_color_classification: Включить классификацию цвета
        """
        self.api_key = api_key or os.getenv("ROBOFLOW_API_KEY")
        self.project_name = project_name
        self.model_version = model_version
        self.confidence_threshold = confidence_threshold
        self.enable_color_classification = enable_color_classification
        
        self.model = None
        self.is_initialized = False
        
        # Кэш детекций для текущего видео
        self.holds_cache: Dict[int, List[Hold]] = {}
        
        # История взаимодействий
        self.interactions: List[HoldInteraction] = []
        self.current_interactions: Dict[str, Optional[HoldInteraction]] = {
            'left_hand': None,
            'right_hand': None,
            'left_foot': None,
            'right_foot': None
        }
        
        # Статистика по зацепам
        self.hold_times: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
            'total_frames': 0,
            'visits': 0,
            'color': 'unknown'
        })
        
        # Инициализация
        if self.api_key and ROBOFLOW_AVAILABLE:
            self._initialize_model()
    
    def _initialize_model(self):
        """Инициализирует модель Roboflow"""
        try:
            rf = Roboflow(api_key=self.api_key)
            project = rf.workspace().project(self.project_name)
            self.model = project.version(self.model_version).model
            self.is_initialized = True
            logger.info(f"✅ Roboflow модель '{self.project_name}' v{self.model_version} инициализирована")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось инициализировать Roboflow: {e}")
            logger.info("Детекция зацепов будет работать в режиме заглушки")
            self.is_initialized = False
    
    def detect_holds(
        self,
        frame: np.ndarray,
        frame_number: int = 0
    ) -> List[Hold]:
        """
        Детектирует зацепы на кадре
        
        Args:
            frame: BGR изображение (numpy array)
            frame_number: Номер кадра для кэширования
            
        Returns:
            Список детектированных зацепов
        """
        # Проверяем кэш
        if frame_number in self.holds_cache:
            return self.holds_cache[frame_number]
        
        if not self.is_initialized:
            # Режим заглушки - возвращаем пустой список
            return []
        
        try:
            # Сохраняем временный файл для Roboflow API
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                cv2.imwrite(tmp.name, frame)
                
                # Вызов API
                predictions = self.model.predict(
                    tmp.name,
                    confidence=int(self.confidence_threshold * 100)
                ).json()
                
                # Удаляем временный файл
                os.unlink(tmp.name)
            
            holds = []
            height, width = frame.shape[:2]
            
            for i, pred in enumerate(predictions.get('predictions', [])):
                # Нормализуем координаты
                x = pred['x'] / width
                y = pred['y'] / height
                w = pred['width'] / width
                h = pred['height'] / height
                
                # Определяем цвет зацепа
                if self.enable_color_classification:
                    color = self._classify_hold_color(frame, pred)
                else:
                    color = pred.get('class', 'unknown')
                
                hold = Hold(
                    id=i,
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    confidence=pred['confidence'],
                    color=color,
                    class_name=pred.get('class', 'hold')
                )
                holds.append(hold)
            
            # Кэшируем результат
            self.holds_cache[frame_number] = holds
            
            return holds
            
        except Exception as e:
            logger.error(f"Ошибка детекции зацепов: {e}")
            return []
    
    def _classify_hold_color(self, frame: np.ndarray, prediction: Dict) -> str:
        """
        Классифицирует цвет зацепа по области изображения
        
        Args:
            frame: BGR изображение
            prediction: Предсказание от Roboflow
            
        Returns:
            Название цвета
        """
        try:
            # Извлекаем область зацепа
            x1 = int(prediction['x'] - prediction['width']/2)
            y1 = int(prediction['y'] - prediction['height']/2)
            x2 = int(prediction['x'] + prediction['width']/2)
            y2 = int(prediction['y'] + prediction['height']/2)
            
            # Границы изображения
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            if x2 <= x1 or y2 <= y1:
                return 'unknown'
            
            roi = frame[y1:y2, x1:x2]
            
            # Конвертируем в HSV для лучшей классификации цвета
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            
            # Средние значения HSV
            avg_h = np.mean(hsv[:, :, 0])
            avg_s = np.mean(hsv[:, :, 1])
            avg_v = np.mean(hsv[:, :, 2])
            
            # Классификация по Hue
            if avg_s < 50:  # Низкая насыщенность
                if avg_v > 200:
                    return 'white'
                elif avg_v < 50:
                    return 'black'
                else:
                    return 'unknown'
            
            # Классификация по оттенку (Hue в OpenCV: 0-180)
            if avg_h < 10 or avg_h > 170:
                return 'red'
            elif avg_h < 25:
                return 'orange'
            elif avg_h < 35:
                return 'yellow'
            elif avg_h < 85:
                return 'green'
            elif avg_h < 130:
                return 'blue'
            elif avg_h < 160:
                return 'purple'
            else:
                return 'pink'
                
        except Exception as e:
            logger.debug(f"Ошибка классификации цвета: {e}")
            return 'unknown'
    
    def match_limb_to_hold(
        self,
        landmarks,
        holds: List[Hold],
        limb: str,
        threshold: float = 0.1
    ) -> Optional[Hold]:
        """
        Сопоставляет конечность с ближайшим зацепом
        
        Args:
            landmarks: MediaPipe pose landmarks
            holds: Список зацепов
            limb: Название конечности ('left_hand', 'right_hand', etc.)
            threshold: Порог расстояния для сопоставления (нормализованный)
            
        Returns:
            Ближайший зацеп или None
        """
        if not holds or landmarks is None:
            return None
        
        keypoint_idx = self.LIMB_KEYPOINTS.get(limb)
        if keypoint_idx is None or keypoint_idx >= len(landmarks.landmark):
            return None
        
        lm = landmarks.landmark[keypoint_idx]
        if lm.visibility < 0.5:
            return None
        
        limb_x, limb_y = lm.x, lm.y
        
        # Находим ближайший зацеп
        min_dist = float('inf')
        closest_hold = None
        
        for hold in holds:
            dist = np.sqrt((hold.x - limb_x)**2 + (hold.y - limb_y)**2)
            if dist < min_dist and dist < threshold:
                min_dist = dist
                closest_hold = hold
        
        return closest_hold
    
    def update_interactions(
        self,
        landmarks,
        holds: List[Hold],
        frame_number: int
    ):
        """
        Обновляет историю взаимодействий с зацепами
        
        Args:
            landmarks: MediaPipe pose landmarks
            holds: Список зацепов на текущем кадре
            frame_number: Номер кадра
        """
        for limb in self.LIMB_KEYPOINTS.keys():
            matched_hold = self.match_limb_to_hold(landmarks, holds, limb)
            current = self.current_interactions[limb]
            
            if matched_hold:
                if current is None:
                    # Новое взаимодействие
                    interaction = HoldInteraction(
                        hold_id=matched_hold.id,
                        limb=limb,
                        start_frame=frame_number,
                        hold_color=matched_hold.color
                    )
                    self.current_interactions[limb] = interaction
                    self.hold_times[matched_hold.id]['visits'] += 1
                    self.hold_times[matched_hold.id]['color'] = matched_hold.color
                    
                elif current.hold_id != matched_hold.id:
                    # Переход на другой зацеп
                    current.end_frame = frame_number
                    current.duration_frames = frame_number - current.start_frame
                    self.interactions.append(current)
                    
                    # Новое взаимодействие
                    interaction = HoldInteraction(
                        hold_id=matched_hold.id,
                        limb=limb,
                        start_frame=frame_number,
                        hold_color=matched_hold.color
                    )
                    self.current_interactions[limb] = interaction
                    self.hold_times[matched_hold.id]['visits'] += 1
                    self.hold_times[matched_hold.id]['color'] = matched_hold.color
                else:
                    # Продолжаем на том же зацепе
                    self.hold_times[matched_hold.id]['total_frames'] += 1
            else:
                if current is not None:
                    # Конец взаимодействия
                    current.end_frame = frame_number
                    current.duration_frames = frame_number - current.start_frame
                    self.interactions.append(current)
                    self.current_interactions[limb] = None
    
    def get_hold_analysis(self, fps: float = 30) -> Dict[str, Any]:
        """
        Возвращает анализ взаимодействия с зацепами
        
        Args:
            fps: Кадров в секунду для конвертации в время
            
        Returns:
            Словарь с анализом
        """
        if not self.interactions and not any(self.current_interactions.values()):
            return {
                'total_holds_used': 0,
                'interactions': [],
                'time_per_hold': {},
                'longest_hold': None,
                'color_distribution': {},
                'analysis_available': False
            }
        
        # Закрываем текущие взаимодействия
        all_interactions = self.interactions.copy()
        for limb, interaction in self.current_interactions.items():
            if interaction is not None:
                all_interactions.append(interaction)
        
        # Анализ времени на зацепах
        time_per_hold = {}
        for hold_id, stats in self.hold_times.items():
            time_per_hold[hold_id] = {
                'time_seconds': stats['total_frames'] / fps,
                'visits': stats['visits'],
                'color': stats['color']
            }
        
        # Находим самый долгий зацеп
        longest_hold = None
        max_time = 0
        for hold_id, data in time_per_hold.items():
            if data['time_seconds'] > max_time:
                max_time = data['time_seconds']
                longest_hold = {
                    'hold_id': hold_id,
                    'time_seconds': data['time_seconds'],
                    'color': data['color']
                }
        
        # Распределение по цветам
        color_distribution = defaultdict(float)
        for hold_id, data in time_per_hold.items():
            color_distribution[data['color']] += data['time_seconds']
        
        return {
            'total_holds_used': len(time_per_hold),
            'total_interactions': len(all_interactions),
            'time_per_hold': time_per_hold,
            'longest_hold': longest_hold,
            'color_distribution': dict(color_distribution),
            'analysis_available': True
        }
    
    def draw_holds_overlay(
        self,
        frame: np.ndarray,
        holds: List[Hold],
        landmarks=None,
        show_connections: bool = True
    ) -> np.ndarray:
        """
        Рисует зацепы и связи с конечностями на кадре
        
        Args:
            frame: BGR изображение
            holds: Список зацепов
            landmarks: MediaPipe landmarks для рисования связей
            show_connections: Показывать линии связи
            
        Returns:
            Изображение с overlay
        """
        height, width = frame.shape[:2]
        
        for hold in holds:
            x1, y1, x2, y2 = hold.get_bbox_pixels(width, height)
            cx, cy = hold.get_center_pixels(width, height)
            
            # Цвет бокса
            color = self.HOLD_COLORS.get(hold.color, self.HOLD_COLORS['unknown'])
            
            # Рисуем прямоугольник
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Рисуем центр
            cv2.circle(frame, (cx, cy), 5, color, -1)
            
            # Подпись с цветом и уверенностью
            label = f"{hold.color} {hold.confidence:.0%}"
            cv2.putText(
                frame, label, (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA
            )
        
        # Рисуем связи с конечностями
        if show_connections and landmarks is not None:
            for limb, keypoint_idx in self.LIMB_KEYPOINTS.items():
                if keypoint_idx >= len(landmarks.landmark):
                    continue
                    
                lm = landmarks.landmark[keypoint_idx]
                if lm.visibility < 0.5:
                    continue
                
                limb_x = int(lm.x * width)
                limb_y = int(lm.y * height)
                
                # Находим ближайший зацеп
                matched = self.match_limb_to_hold(landmarks, holds, limb)
                if matched:
                    cx, cy = matched.get_center_pixels(width, height)
                    
                    # Цвет линии в зависимости от конечности
                    if 'hand' in limb:
                        line_color = (0, 255, 0)  # Зеленый для рук
                    else:
                        line_color = (255, 165, 0)  # Оранжевый для ног
                    
                    cv2.line(frame, (limb_x, limb_y), (cx, cy), line_color, 2, cv2.LINE_AA)
        
        return frame
    
    def format_holds_report(self, fps: float = 30) -> str:
        """
        Форматирует отчет о взаимодействии с зацепами
        
        Args:
            fps: FPS видео
            
        Returns:
            Форматированный текст отчета
        """
        analysis = self.get_hold_analysis(fps)
        
        if not analysis['analysis_available']:
            return """
🎯 АНАЛИЗ ЗАЦЕПОВ
━━━━━━━━━━━━━━━━━━━━━
⚠️ Детекция зацепов недоступна
Для активации добавьте ROBOFLOW_API_KEY в .env
"""
        
        report = """
🎯 АНАЛИЗ ЗАЦЕПОВ (BoulderVision)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 ОБЩАЯ СТАТИСТИКА:
"""
        report += f"• Использовано зацепов: {analysis['total_holds_used']}\n"
        report += f"• Всего взаимодействий: {analysis['total_interactions']}\n"
        
        # Самый долгий зацеп
        if analysis['longest_hold']:
            lh = analysis['longest_hold']
            report += f"\n⏱️ САМЫЙ ДОЛГИЙ ЗАЦЕП:\n"
            report += f"• Цвет: {lh['color']}\n"
            report += f"• Время: {lh['time_seconds']:.1f} сек\n"
            
            if lh['time_seconds'] > 3:
                report += f"💡 Ты слишком долго думал на {lh['color']} зацепе!\n"
        
        # Распределение по цветам
        if analysis['color_distribution']:
            report += f"\n🎨 ВРЕМЯ ПО ЦВЕТАМ:\n"
            sorted_colors = sorted(
                analysis['color_distribution'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for color, time in sorted_colors:
                report += f"• {color}: {time:.1f} сек\n"
        
        return report
    
    def reset(self):
        """Сброс состояния для нового видео"""
        self.holds_cache.clear()
        self.interactions.clear()
        self.current_interactions = {
            'left_hand': None,
            'right_hand': None,
            'left_foot': None,
            'right_foot': None
        }
        self.hold_times.clear()
