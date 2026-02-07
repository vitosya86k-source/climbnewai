"""
BoulderVision Метрики движения

Основано на:
1. https://github.com/reiffd7/BoulderVision - оригинальный код
2. https://cs231n.stanford.edu/2024/papers/using-pose-estimation-to-analyze-rock-climbing-technique.pdf

Метрики BoulderVision:
- Velocity Ratio: отношение текущей скорости к средней за окно
- Cumulative Distance: накопленная дистанция всех кадров
- Trajectory Similarity: косинусное сходство траекторий

Метрики Stanford PDF:
- Trajectory Efficiency Score: оценка эффективности траектории CoM
- Straight Arms Efficiency Score: оценка эффективности прямых рук
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from collections import deque
import logging

logger = logging.getLogger(__name__)


class KeypointsHistory:
    """
    Буфер для хранения истории ключевых точек
    Адаптировано из BoulderVision: calculate_movement_custom_block.py
    """
    
    # MediaPipe Pose - 33 точки, но нам нужны аналоги COCO 17 точек
    # COCO keypoints mapping для совместимости с BoulderVision
    COCO_KEYPOINTS = {
        'nose': 0,
        'left_shoulder': 11,
        'right_shoulder': 12,
        'left_elbow': 13,
        'right_elbow': 14,
        'left_wrist': 15,
        'right_wrist': 16,
        'left_hip': 23,
        'right_hip': 24,
        'left_knee': 25,
        'right_knee': 26,
        'left_ankle': 27,
        'right_ankle': 28
    }
    
    # Точки для отслеживания контакта с зацепами (как в BoulderVision)
    CONTACT_POINTS = {
        'left_wrist': 15,
        'right_wrist': 16,
        'left_ankle': 27,
        'right_ankle': 28
    }
    
    def __init__(self, buffer_size: int = 30, num_keypoints: int = 17):
        """
        Args:
            buffer_size: Размер буфера истории (window_size в BoulderVision)
            num_keypoints: Количество ключевых точек (17 для COCO формата)
        """
        self.buffer_size = buffer_size
        self.num_keypoints = num_keypoints
        
        # История в формате BoulderVision: (buffer_size, 1, num_keypoints, 2)
        # Инициализируем нулями как в оригинале
        self.history = np.zeros((buffer_size, 1, num_keypoints, 2), dtype=np.float32)
        self.timestamps: deque = deque(maxlen=buffer_size)
        self.frame_count = 0
        
    def add_frame(self, landmarks, timestamp: float):
        """
        Добавляет кадр в историю в формате BoulderVision
        """
        if landmarks is None:
            return
        
        # Извлекаем координаты в формат (num_keypoints, 2)
        keypoints_xy = np.zeros((self.num_keypoints, 2), dtype=np.float32)
        
        # Конвертируем MediaPipe в COCO-подобный формат
        mp_to_coco = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 0, 0, 0, 0]
        
        for coco_idx, mp_idx in enumerate(mp_to_coco[:self.num_keypoints]):
            if mp_idx < len(landmarks.landmark):
                lm = landmarks.landmark[mp_idx]
                if lm.visibility > 0.3:
                    keypoints_xy[coco_idx] = [lm.x, lm.y]
        
        # Сдвигаем историю как в BoulderVision: np.roll(keypoints_history, -1, axis=0)
        self.history = np.roll(self.history, -1, axis=0)
        self.history[-1] = keypoints_xy[np.newaxis, ...]  # Shape: (1, num_keypoints, 2)
        
        self.timestamps.append(timestamp)
        self.frame_count += 1
    
    def get_current_keypoints(self) -> np.ndarray:
        """Возвращает текущие (последние) ключевые точки"""
        return self.history[-1]
    
    def is_ready(self) -> bool:
        """Достаточно ли данных для анализа"""
        # Проверяем количество ненулевых кадров как в BoulderVision
        non_zero_frames = np.any(self.history != 0, axis=(2, 3))
        return np.sum(non_zero_frames) >= 5  # Минимум 5 валидных кадров
    
    def clear(self):
        """Очистка буфера"""
        self.history = np.zeros_like(self.history)
        self.timestamps.clear()
        self.frame_count = 0


def compute_trajectory_similarities(
    history: np.ndarray,
    new_points: np.ndarray,
    window_size: int
) -> Dict[str, Any]:
    """
    Вычисляет метрики движения - ОРИГИНАЛЬНЫЙ АЛГОРИТМ из BoulderVision
    
    Из: custom_python_blcoks/calculate_movement_custom_block.py
    
    Args:
        history: История keypoints shape (buffer_size, 1, num_keypoints, 2)
        new_points: Новые keypoints shape (1, num_keypoints, 2)
        window_size: Размер окна для расчетов
    
    Returns:
        dict с метриками:
        - trajectory_similarity: косинусное сходство траекторий
        - velocity_ratio: отношение текущей скорости к средней
        - cumulative_distance: накопленная дистанция
    """
    
    # Значения по умолчанию как в BoulderVision
    default_similarities = {
        'trajectory_similarity': None,
        'velocity_ratio': 1.0,
        'cumulative_distance': 0.0,  # сумма по окну (историческое определение)
        'current_velocity': 0.0,
        'frame_distance': 0.0,       # дистанция за текущий шаг
    }
    
    # Проверяем количество ненулевых кадров в истории
    non_zero_frames = np.any(history != 0, axis=(2, 3))
    valid_frame_count = np.sum(non_zero_frames)
    
    if valid_frame_count < window_size or len(new_points) == 0:
        return default_similarities
    
    try:
        # 1. Trajectory vectors - движение за окно
        history_trajectory = history[-1] - history[-window_size]  # Total movement over window
        new_trajectory = new_points - history[-window_size]       # Movement from start of window
        
        # 2. Velocity vectors - последовательные разности
        history_velocities = np.diff(history[-window_size:], axis=0)  # Shape: (window_size-1, 1, 17, 2)
        new_velocity = new_points - history[-1]
        
        # Flatten для расчетов
        history_trajectory_flat = history_trajectory.reshape(-1)
        new_trajectory_flat = new_trajectory.reshape(-1)
        
        # 1. TRAJECTORY SIMILARITY (косинусное сходство)
        norm_hist = np.linalg.norm(history_trajectory_flat)
        norm_new = np.linalg.norm(new_trajectory_flat)
        
        if norm_hist > 1e-8 and norm_new > 1e-8:
            trajectory_cos_sim = np.dot(history_trajectory_flat, new_trajectory_flat) / (norm_hist * norm_new)
        else:
            trajectory_cos_sim = None
        
        # 2. VELOCITY RATIO
        velocity_magnitudes = np.linalg.norm(history_velocities.reshape(window_size-1, -1), axis=1)
        avg_history_velocity = np.mean(velocity_magnitudes)
        new_velocity_magnitude = np.linalg.norm(new_velocity.reshape(-1))
        
        if avg_history_velocity > 1e-8:
            velocity_ratio = new_velocity_magnitude / avg_history_velocity
        else:
            velocity_ratio = 1.0
        
        # 3. CUMULATIVE DISTANCE (сумма по окну, для совместимости)
        cumulative_distance = np.sum(velocity_magnitudes)
        # 4. Frame distance (дистанция текущего шага)
        frame_distance = new_velocity_magnitude
        
        return {
            'trajectory_similarity': float(trajectory_cos_sim) if trajectory_cos_sim is not None else None,
            'velocity_ratio': float(np.clip(velocity_ratio, 0.01, 10.0)),
            'cumulative_distance': float(cumulative_distance),
            'current_velocity': float(new_velocity_magnitude),
            'frame_distance': float(frame_distance),
        }
        
    except Exception as e:
        logger.warning(f"Ошибка в compute_trajectory_similarities: {e}")
        return default_similarities


def compute_trajectory_efficiency(
    com_history: List[Tuple[float, float]],
    start_point: Tuple[float, float],
    end_point: Tuple[float, float]
) -> float:
    """
    Вычисляет Trajectory Efficiency Score из Stanford PDF
    
    "trajectory efficiency as well as elbow flexion"
    
    Формула: Прямое расстояние / Фактически пройденный путь
    Чем ближе к 1, тем эффективнее траектория (меньше лишних движений)
    
    Args:
        com_history: История позиций центра масс [(x, y), ...]
        start_point: Начальная точка
        end_point: Конечная точка
    
    Returns:
        float: Оценка эффективности [0, 1]
    """
    if len(com_history) < 2:
        return 1.0
    
    # Прямое (идеальное) расстояние
    direct_distance = np.sqrt(
        (end_point[0] - start_point[0])**2 + 
        (end_point[1] - start_point[1])**2
    )
    
    if direct_distance < 0.001:
        return 1.0  # Не было движения
    
    # Фактически пройденный путь
    actual_distance = 0.0
    for i in range(1, len(com_history)):
        actual_distance += np.sqrt(
            (com_history[i][0] - com_history[i-1][0])**2 +
            (com_history[i][1] - com_history[i-1][1])**2
        )
    
    if actual_distance < 0.001:
        return 1.0
    
    # Эффективность = прямой путь / фактический путь
    efficiency = min(direct_distance / actual_distance, 1.0)
    
    return round(efficiency, 2)


def compute_straight_arms_efficiency(
    elbow_angles: List[float]
) -> float:
    """
    Вычисляет Straight Arms Efficiency Score из Stanford PDF
    
    "climbers are still always in the process of refining them"
    "minimizing the use of arm muscles"
    
    Прямые руки (угол ~180°) экономят энергию.
    Согнутые руки (угол < 120°) тратят больше сил.
    
    Args:
        elbow_angles: Список углов в локтях (в градусах)
    
    Returns:
        float: Оценка эффективности [0, 1]
    """
    if not elbow_angles:
        return 1.0
    
    # Нормализуем углы: 180° = 1.0 (идеально), 90° = 0.5, 0° = 0.0
    efficiencies = []
    for angle in elbow_angles:
        # Угол от 0 до 180
        normalized = min(max(angle, 0), 180) / 180.0
        efficiencies.append(normalized)
    
    return round(np.mean(efficiencies), 2)


class BoulderVisionMetrics:
    """
    Класс для вычисления метрик BoulderVision + Stanford PDF
    
    Объединяет:
    1. BoulderVision метрики (velocity_ratio, cumulative_distance, trajectory_similarity)
    2. Stanford метрики (trajectory_efficiency, straight_arms_efficiency)
    """
    
    def __init__(self, buffer_size: int = 30, window_size: int = 10):
        """
        Args:
            buffer_size: Размер буфера истории
            window_size: Окно для расчета BoulderVision метрик
        """
        self.keypoints_history = KeypointsHistory(buffer_size)
        self.window_size = window_size
        
        # BoulderVision накопленные метрики
        self.all_velocity_ratios: List[float] = []
        self.all_trajectory_similarities: List[float] = []
        self.all_frame_distances: List[float] = []  # дистанция за шаг
        self.total_cumulative_distance: float = 0   # сумма frame_distance
        
        # Stanford метрики
        self.com_history: List[Tuple[float, float]] = []  # Центр масс
        self.elbow_angles_history: List[float] = []  # Углы локтей
        
        # Тепловая карта - все позиции
        self.all_positions: List[Tuple[float, float]] = []
        
        # Траектории конкретных точек для визуализации
        self.trajectories: Dict[str, List[Tuple[float, float]]] = {
            'left_wrist': [],
            'right_wrist': [],
            'left_ankle': [],
            'right_ankle': [],
            'nose': []
        }
        
        # Анализ зон
        self.time_in_zones: Dict[str, float] = {'lower': 0, 'middle': 0, 'upper': 0}
        
        # Пиковые моменты
        self.peak_velocity_frame: Optional[int] = None
        self.peak_velocity_value: float = 0
        
        self.frame_count = 0
    
    def process_frame(
        self,
        landmarks,
        frame_number: int,
        timestamp: float
    ) -> Dict[str, Any]:
        """
        Обрабатывает один кадр и возвращает метрики
        """
        self.frame_count += 1
        
        # Добавляем в историю
        self.keypoints_history.add_frame(landmarks, timestamp)
        
        # BoulderVision метрики
        bv_metrics = {
            'trajectory_similarity': None,
            'velocity_ratio': 1.0,
            'cumulative_distance': 0.0,
            'current_velocity': 0.0,
            'frame_distance': 0.0,
        }
        
        if self.keypoints_history.is_ready():
            current_keypoints = self.keypoints_history.get_current_keypoints()
            bv_metrics = compute_trajectory_similarities(
                self.keypoints_history.history,
                current_keypoints,
                self.window_size
            )
        
        # Сохраняем для статистики
        if bv_metrics['velocity_ratio'] is not None:
            self.all_velocity_ratios.append(bv_metrics['velocity_ratio'])
            
            # Пиковая скорость
            if bv_metrics['velocity_ratio'] > self.peak_velocity_value:
                self.peak_velocity_value = bv_metrics['velocity_ratio']
                self.peak_velocity_frame = frame_number
        
        if bv_metrics['trajectory_similarity'] is not None:
            self.all_trajectory_similarities.append(bv_metrics['trajectory_similarity'])
        
        # Копим по кадрам
        frame_dist = bv_metrics.get('frame_distance', 0.0)
        self.all_frame_distances.append(frame_dist)
        self.total_cumulative_distance += frame_dist
        
        # Собираем данные для тепловой карты и траекторий
        self._collect_positions(landmarks)
        
        # Обновляем зоны времени
        self._update_time_zones(landmarks)
        
        return {
            'frame_number': frame_number,
            'timestamp': timestamp,
            **bv_metrics
        }
    
    def _collect_positions(self, landmarks):
        """Собирает позиции для тепловой карты и траекторий"""
        if landmarks is None:
            return
        
        # Для тепловой карты - все видимые точки
        for idx in range(33):
            if idx < len(landmarks.landmark):
                lm = landmarks.landmark[idx]
                if lm.visibility > 0.5:
                    self.all_positions.append((lm.x, lm.y))
        
        # Ограничиваем размер
        max_positions = 10000
        if len(self.all_positions) > max_positions:
            self.all_positions = self.all_positions[-max_positions:]
        
        # Траектории конкретных точек
        trajectory_mapping = {
            'left_wrist': 15, 'right_wrist': 16,
            'left_ankle': 27, 'right_ankle': 28,
            'nose': 0
        }
        
        for name, idx in trajectory_mapping.items():
            if idx < len(landmarks.landmark):
                lm = landmarks.landmark[idx]
                if lm.visibility > 0.5:
                    self.trajectories[name].append((lm.x, lm.y))
                    
                    # Ограничиваем длину
                    max_traj = 1000
                    if len(self.trajectories[name]) > max_traj:
                        self.trajectories[name] = self.trajectories[name][-max_traj:]
        
        # Центр масс для trajectory_efficiency
        com = self._compute_center_of_mass(landmarks)
        if com is not None:
            self.com_history.append(com)
        
        # Углы локтей для straight_arms_efficiency
        elbow_angle = self._compute_elbow_angles(landmarks)
        if elbow_angle is not None:
            self.elbow_angles_history.extend(elbow_angle)
    
    def _compute_center_of_mass(self, landmarks) -> Optional[Tuple[float, float]]:
        """Вычисляет центр масс"""
        if landmarks is None:
            return None
        
        # Используем плечи и бедра для CoM
        key_points = [11, 12, 23, 24]
        x_values, y_values = [], []
        
        for idx in key_points:
            if idx < len(landmarks.landmark):
                lm = landmarks.landmark[idx]
                if lm.visibility > 0.3:
                    x_values.append(lm.x)
                    y_values.append(lm.y)
        
        if x_values:
            return (np.mean(x_values), np.mean(y_values))
        return None
    
    def _compute_elbow_angles(self, landmarks) -> Optional[List[float]]:
        """Вычисляет углы в локтях"""
        if landmarks is None:
            return None
        
        angles = []
        
        # Левый локоть: плечо(11) - локоть(13) - запястье(15)
        left_angle = self._angle_between_points(landmarks, 11, 13, 15)
        if left_angle:
            angles.append(left_angle)
        
        # Правый локоть: плечо(12) - локоть(14) - запястье(16)
        right_angle = self._angle_between_points(landmarks, 12, 14, 16)
        if right_angle:
            angles.append(right_angle)
        
        return angles if angles else None
    
    def _angle_between_points(self, landmarks, p1_idx, p2_idx, p3_idx) -> Optional[float]:
        """Вычисляет угол между тремя точками"""
        try:
            p1 = landmarks.landmark[p1_idx]
            p2 = landmarks.landmark[p2_idx]
            p3 = landmarks.landmark[p3_idx]
            
            if p1.visibility < 0.3 or p2.visibility < 0.3 or p3.visibility < 0.3:
                return None
            
            v1 = np.array([p1.x - p2.x, p1.y - p2.y])
            v2 = np.array([p3.x - p2.x, p3.y - p2.y])
            
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
            angle = np.arccos(np.clip(cos_angle, -1, 1))
            
            return np.degrees(angle)
        except:
            return None
    
    def _update_time_zones(self, landmarks):
        """Обновляет время нахождения в разных зонах"""
        if landmarks is None:
            return
        
        com = self._compute_center_of_mass(landmarks)
        if com is None:
            return
        
        _, avg_y = com
        
        # В MediaPipe y=0 это верх, y=1 это низ
        if avg_y < 0.33:
            self.time_in_zones['upper'] += 1
        elif avg_y < 0.66:
            self.time_in_zones['middle'] += 1
        else:
            self.time_in_zones['lower'] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Возвращает итоговую статистику за всё видео
        
        Включает метрики BoulderVision + Stanford
        """
        if not self.all_velocity_ratios:
            return self._get_empty_summary()
        
        # BoulderVision статистика
        avg_vr = np.mean(self.all_velocity_ratios)
        max_vr = np.max(self.all_velocity_ratios)
        min_vr = np.min(self.all_velocity_ratios)
        std_vr = np.std(self.all_velocity_ratios)
        
        # Trajectory similarity
        avg_traj_sim = np.mean(self.all_trajectory_similarities) if self.all_trajectory_similarities else None
        
        # Stanford: Trajectory Efficiency
        trajectory_efficiency = 1.0
        if len(self.com_history) >= 2:
            trajectory_efficiency = compute_trajectory_efficiency(
                self.com_history,
                self.com_history[0],
                self.com_history[-1]
            )
        
        # Stanford: Straight Arms Efficiency
        straight_arms_efficiency = compute_straight_arms_efficiency(self.elbow_angles_history)
        
        # Паттерн движения
        movement_pattern = self._classify_movement_pattern(avg_vr, std_vr)
        
        # Зоны в процентах
        total_zone_time = sum(self.time_in_zones.values())
        zone_percentages = {}
        if total_zone_time > 0:
            for zone, time in self.time_in_zones.items():
                zone_percentages[zone] = round(time / total_zone_time * 100, 1)
        else:
            zone_percentages = {'lower': 0, 'middle': 0, 'upper': 0}
        
        return {
            # BoulderVision метрики
            'avg_velocity_ratio': round(avg_vr, 2),
            'max_velocity_ratio': round(max_vr, 2),
            'min_velocity_ratio': round(min_vr, 2),
            'velocity_std': round(std_vr, 2),
            'avg_trajectory_similarity': round(avg_traj_sim, 3) if avg_traj_sim is not None else None,
            'total_distance': round(self.total_cumulative_distance, 4),
            'avg_frame_distance': round(np.mean(self.all_frame_distances), 4) if self.all_frame_distances else 0.0,
            
            # Stanford метрики
            'trajectory_efficiency': trajectory_efficiency,
            'straight_arms_efficiency': straight_arms_efficiency,
            
            # Пиковые моменты
            'peak_velocity_frame': self.peak_velocity_frame,
            'peak_velocity_value': round(self.peak_velocity_value, 2),
            
            # Зоны времени
            'time_zones': zone_percentages,
            
            # Паттерн движения
            'movement_pattern': movement_pattern,
            
            # Статистика
            'total_frames_analyzed': self.frame_count,
            'heatmap_positions_count': len(self.all_positions)
        }
    
    def _get_empty_summary(self) -> Dict[str, Any]:
        """Возвращает пустую статистику"""
        return {
            'avg_velocity_ratio': 1.0,
            'max_velocity_ratio': 1.0,
            'min_velocity_ratio': 1.0,
            'velocity_std': 0.0,
            'avg_trajectory_similarity': None,
            'total_distance': 0,
            'avg_frame_distance': 0.0,
            'trajectory_efficiency': 1.0,
            'straight_arms_efficiency': 1.0,
            'peak_velocity_frame': None,
            'peak_velocity_value': 0,
            'time_zones': {'lower': 0, 'middle': 0, 'upper': 0},
            'movement_pattern': 'unknown',
            'total_frames_analyzed': 0,
            'heatmap_positions_count': 0
        }
    
    def _classify_movement_pattern(self, avg_vr: float, std_vr: float) -> str:
        """
        Классифицирует паттерн движения
        """
        if std_vr < 0.3:
            if avg_vr > 1.2:
                return "dynamic_consistent"
            elif avg_vr < 0.8:
                return "slow_controlled"
            else:
                return "steady_pace"
        else:
            if avg_vr > 1.2:
                return "explosive_bursts"
            elif avg_vr < 0.8:
                return "hesitant"
            else:
                return "variable"
    
    def get_heatmap_data(self) -> List[Tuple[float, float]]:
        """Возвращает данные для тепловой карты"""
        return self.all_positions
    
    def get_trajectory_data(self, keypoint: str = 'left_wrist') -> List[Tuple[float, float]]:
        """Возвращает траекторию конкретной точки"""
        return self.trajectories.get(keypoint, [])
    
    def reset(self):
        """Сброс всех метрик для нового видео"""
        self.keypoints_history.clear()
        self.all_velocity_ratios.clear()
        self.all_trajectory_similarities.clear()
        self.total_cumulative_distance = 0
        self.com_history.clear()
        self.elbow_angles_history.clear()
        self.all_positions.clear()
        for key in self.trajectories:
            self.trajectories[key].clear()
        self.time_in_zones = {'lower': 0, 'middle': 0, 'upper': 0}
        self.peak_velocity_frame = None
        self.peak_velocity_value = 0
        self.frame_count = 0


def format_movement_analysis(summary: Dict[str, Any]) -> str:
    """
    Форматирует анализ движения для отчета
    
    Включает BoulderVision + Stanford метрики
    """
    
    pattern_descriptions = {
        'dynamic_consistent': '🚀 Динамичный стабильный стиль',
        'slow_controlled': '🧘 Медленный контролируемый стиль',
        'steady_pace': '⚖️ Ровный темп',
        'explosive_bursts': '💥 Взрывной стиль',
        'hesitant': '🤔 Нерешительный стиль',
        'variable': '🎢 Переменный темп',
        'unknown': '❓ Недостаточно данных'
    }
    
    pattern = summary.get('movement_pattern', 'unknown')
    zones = summary.get('time_zones', {})
    
    # Stanford эффективность
    traj_eff = summary.get('trajectory_efficiency', 1.0)
    arms_eff = summary.get('straight_arms_efficiency', 1.0)
    
    analysis = f"""
📊 BOULDERVISION + STANFORD АНАЛИЗ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 ПАТТЕРН ДВИЖЕНИЯ:
{pattern_descriptions.get(pattern, pattern)}

⚡ ДИНАМИКА СКОРОСТИ (BoulderVision):
• Средний velocity ratio: {summary.get('avg_velocity_ratio', 1.0):.2f}x
• Макс. ускорение: {summary.get('max_velocity_ratio', 1.0):.2f}x
• Вариативность: {summary.get('velocity_std', 0):.2f}

📏 НАКОПЛЕННАЯ ДИСТАНЦИЯ:
• Общий путь: {summary.get('total_distance', 0):.4f}

🎯 ЭФФЕКТИВНОСТЬ (Stanford):
• Trajectory Efficiency: {traj_eff:.0%} {"✅" if traj_eff > 0.7 else "⚠️"}
• Straight Arms Efficiency: {arms_eff:.0%} {"✅" if arms_eff > 0.6 else "⚠️"}

🗺️ РАСПРЕДЕЛЕНИЕ ВРЕМЕНИ:
• Верхняя зона: {zones.get('upper', 0)}%
• Средняя зона: {zones.get('middle', 0)}%
• Нижняя зона: {zones.get('lower', 0)}%
"""
    
    # Интерпретация
    analysis += "\n💡 РЕКОМЕНДАЦИИ:\n"
    
    if traj_eff < 0.7:
        analysis += "• Траектория: слишком много лишних движений - работайте над экономичностью\n"
    else:
        analysis += "• Траектория: хорошая экономичность движений\n"
    
    if arms_eff < 0.6:
        analysis += "• Руки: часто согнуты - старайтесь чаще выпрямлять руки для экономии сил\n"
    else:
        analysis += "• Руки: хорошо используете прямые руки\n"
    
    return analysis.strip()
