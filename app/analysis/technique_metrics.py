"""
7 базовых метрик техники скалолазания
Основано на методологии Eric J. Hörst «Training for Climbing»

Метрики:
1. Quiet Feet (Точность ног)
2. Hip Position (Положение таза)
3. Противовес (Diagonal Movement)
4. Считывание (Route Reading)
5. Ритм (Movement Rhythm)
6. Контроль динамики (Dynamic Control)
7. Grip Release (Мягкость перехватов)
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Any, Optional
from collections import deque
import logging

logger = logging.getLogger(__name__)


class TechniqueMetricsAnalyzer:
    """Анализатор 7 базовых метрик техники"""
    ROTATION_THRESHOLD_DEG = 15.0
    POSITION_THRESHOLD = 0.02
    
    def __init__(self, history_size: int = 90):
        """
        Args:
            history_size: размер истории для анализа (90 кадров = 3 сек при 30 FPS)
        """
        self.history_size = history_size
        
        # История позиций для анализа
        self.foot_positions_history: Dict[str, List[Tuple[float, float, int]]] = {
            'left': [],   # [(x, y, frame_number), ...]
            'right': []   # [(x, y, frame_number), ...]
        }
        self.foot_angle_history: Dict[str, List[float]] = {
            'left': [],
            'right': []
        }
        
        self.hand_positions_history: Dict[str, List[Tuple[float, float, int]]] = {
            'left': [],
            'right': []
        }
        
        self.movement_intervals: List[float] = []  # Интервалы между движениями (мс)
        self.last_movement_time: Optional[float] = None
        
        self.dynamic_moves: List[Dict[str, Any]] = []  # Динамические движения
        self.hand_trajectories: List[List[Tuple[float, float, float]]] = []  # Траектории рук
        self.hand_moves_count: int = 0
        self.dynamic_moves_count: int = 0
        self.max_reach_ratio: float = 0.0
        self._last_dynamic_frame: Dict[str, int] = {'left': -999, 'right': -999}
        
        self.route_reading_data: Dict[str, Any] = {
            'first_movement_time': None,
            'reading_pauses': [],
            'total_duration': None
        }
        
        self.frame_number = 0
        
    def reset(self):
        """Сброс всех историй"""
        self.foot_positions_history = {'left': [], 'right': []}
        self.foot_angle_history = {'left': [], 'right': []}
        self.hand_positions_history = {'left': [], 'right': []}
        self.movement_intervals = []
        self.last_movement_time = None
        self.dynamic_moves = []
        self.hand_trajectories = []
        self.hand_moves_count = 0
        self.dynamic_moves_count = 0
        self.max_reach_ratio = 0.0
        self._last_dynamic_frame = {'left': -999, 'right': -999}
        self.route_reading_data = {
            'first_movement_time': None,
            'reading_pauses': [],
            'total_duration': None
        }
        self.frame_number = 0
    
    def analyze_frame(
        self,
        landmarks,
        frame_number: int,
        timestamp: float,
        frame_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Анализ кадра и вычисление метрик
        
        Args:
            landmarks: MediaPipe landmarks
            frame_number: номер кадра
            timestamp: временная метка (секунды)
            frame_data: дополнительные данные кадра
            
        Returns:
            dict с метриками {metric_name: score (0-100)}
        """
        self.frame_number = frame_number
        
        if not landmarks:
            return self._get_default_metrics()
        
        # Обновляем историю позиций
        moved = self._update_positions_history(landmarks, frame_number, timestamp)
        if moved:
            self.hand_moves_count += 1

        # Обновляем разлёт рук относительно роста (оценка растяжек)
        self._update_reach_ratio(landmarks)

        # Считаем динамические движения на текущем кадре
        self._update_dynamic_moves(landmarks, timestamp)
        
        # Вычисляем метрики
        metrics = {
            'quiet_feet': self._calculate_quiet_feet(),
            'hip_position': self._calculate_hip_position(landmarks),
            'diagonal': self._calculate_diagonal_coordination(),
            'route_reading': self._calculate_route_reading(timestamp),
            'rhythm': self._calculate_rhythm_stability(),
            'dynamic_control': self._calculate_dynamic_control(),
            'grip_release': self._calculate_grip_release()
        }
        
        return metrics
    
    def _update_positions_history(self, landmarks, frame_number: int, timestamp: float) -> bool:
        """Обновление истории позиций конечностей"""
        h, w = 1.0, 1.0  # Нормализованные координаты MediaPipe
        moved_this_frame = False
        
        # Стопы (лодыжки)
        left_ankle = landmarks.landmark[27] if len(landmarks.landmark) > 27 else None
        right_ankle = landmarks.landmark[28] if len(landmarks.landmark) > 28 else None
        
        if left_ankle and left_ankle.visibility > 0.5:
            self.foot_positions_history['left'].append((left_ankle.x, left_ankle.y, frame_number))
            self.foot_angle_history['left'].append(self._calc_foot_angle(landmarks.landmark, 'left'))
            if len(self.foot_positions_history['left']) > self.history_size:
                self.foot_positions_history['left'].pop(0)
            if len(self.foot_angle_history['left']) > self.history_size:
                self.foot_angle_history['left'].pop(0)
        
        if right_ankle and right_ankle.visibility > 0.5:
            self.foot_positions_history['right'].append((right_ankle.x, right_ankle.y, frame_number))
            self.foot_angle_history['right'].append(self._calc_foot_angle(landmarks.landmark, 'right'))
            if len(self.foot_positions_history['right']) > self.history_size:
                self.foot_positions_history['right'].pop(0)
            if len(self.foot_angle_history['right']) > self.history_size:
                self.foot_angle_history['right'].pop(0)
        
        # Руки (запястья)
        left_wrist = landmarks.landmark[15] if len(landmarks.landmark) > 15 else None
        right_wrist = landmarks.landmark[16] if len(landmarks.landmark) > 16 else None
        
        if left_wrist and left_wrist.visibility > 0.5:
            self.hand_positions_history['left'].append((left_wrist.x, left_wrist.y, timestamp))
            if len(self.hand_positions_history['left']) > self.history_size:
                self.hand_positions_history['left'].pop(0)
        
        if right_wrist and right_wrist.visibility > 0.5:
            self.hand_positions_history['right'].append((right_wrist.x, right_wrist.y, timestamp))
            if len(self.hand_positions_history['right']) > self.history_size:
                self.hand_positions_history['right'].pop(0)
        
        # Определяем движение (если рука или нога переместилась значительно)
        movement_threshold = 0.02  # 2% от размера кадра
        
        for side in ['left', 'right']:
            if self.hand_positions_history[side] and len(self.hand_positions_history[side]) > 1:
                prev = self.hand_positions_history[side][-2]
                curr = self.hand_positions_history[side][-1]
                dist = math.sqrt((curr[0] - prev[0])**2 + (curr[1] - prev[1])**2)
                if dist > movement_threshold:
                    moved_this_frame = True
                    if self.last_movement_time is not None:
                        interval_ms = (timestamp - self.last_movement_time) * 1000
                        if interval_ms > 0:
                            self.movement_intervals.append(interval_ms)
                            if len(self.movement_intervals) > 30:
                                self.movement_intervals.pop(0)
                    self.last_movement_time = timestamp

        return moved_this_frame

    def _update_dynamic_moves(self, landmarks, timestamp: float) -> None:
        """Фиксирует динамические движения рук (для video_stats)."""
        window = 5
        dt = window * 0.033  # ~30 FPS
        velocity_threshold = 0.05
        if not landmarks:
            return

        for side, idx in [('left', 15), ('right', 16)]:
            if len(landmarks.landmark) <= idx:
                continue
            lm = landmarks.landmark[idx]
            if lm.visibility < 0.5:
                continue

            positions = self.hand_positions_history[side]
            if len(positions) < window + 1:
                continue

            prev = positions[-(window + 1)]
            curr = positions[-1]
            dist = math.sqrt((curr[0] - prev[0])**2 + (curr[1] - prev[1])**2)
            velocity = dist / dt if dt > 0 else 0

            if velocity > velocity_threshold:
                if self.frame_number - self._last_dynamic_frame[side] > window:
                    self.dynamic_moves_count += 1
                    self._last_dynamic_frame[side] = self.frame_number

    def _update_reach_ratio(self, landmarks) -> None:
        """Оценивает разлёт рук относительно роста (max_reach_ratio)."""
        try:
            left_wrist = landmarks.landmark[15] if len(landmarks.landmark) > 15 else None
            right_wrist = landmarks.landmark[16] if len(landmarks.landmark) > 16 else None
            left_shoulder = landmarks.landmark[11] if len(landmarks.landmark) > 11 else None
            right_shoulder = landmarks.landmark[12] if len(landmarks.landmark) > 12 else None
            left_ankle = landmarks.landmark[27] if len(landmarks.landmark) > 27 else None
            right_ankle = landmarks.landmark[28] if len(landmarks.landmark) > 28 else None

            if not all([left_wrist, right_wrist, left_shoulder, right_shoulder]):
                return
            if any([lm.visibility < 0.5 for lm in [left_wrist, right_wrist, left_shoulder, right_shoulder]]):
                return

            wrist_dist = math.sqrt(
                (left_wrist.x - right_wrist.x) ** 2 +
                (left_wrist.y - right_wrist.y) ** 2
            )

            heights = []
            if left_ankle and left_ankle.visibility > 0.5:
                heights.append(math.sqrt((left_shoulder.x - left_ankle.x) ** 2 + (left_shoulder.y - left_ankle.y) ** 2))
            if right_ankle and right_ankle.visibility > 0.5:
                heights.append(math.sqrt((right_shoulder.x - right_ankle.x) ** 2 + (right_shoulder.y - right_ankle.y) ** 2))

            if heights:
                height = sum(heights) / len(heights)
            else:
                # fallback: плечи → таз
                left_hip = landmarks.landmark[23] if len(landmarks.landmark) > 23 else None
                right_hip = landmarks.landmark[24] if len(landmarks.landmark) > 24 else None
                if not all([left_hip, right_hip]):
                    return
                if any([lm.visibility < 0.5 for lm in [left_hip, right_hip]]):
                    return
                hip_center = ((left_hip.x + right_hip.x) / 2, (left_hip.y + right_hip.y) / 2)
                shoulder_center = ((left_shoulder.x + right_shoulder.x) / 2, (left_shoulder.y + right_shoulder.y) / 2)
                height = math.sqrt(
                    (shoulder_center[0] - hip_center[0]) ** 2 +
                    (shoulder_center[1] - hip_center[1]) ** 2
                )

            if height > 0:
                ratio = wrist_dist / height
                if ratio > self.max_reach_ratio:
                    self.max_reach_ratio = ratio
        except Exception:
            return
    
    def _calculate_quiet_feet(self) -> float:
        """
        Quiet Feet (Точность ног)
        Количество перестановок ноги на одной точке опоры
        """
        if len(self.foot_positions_history['left']) < 5 and len(self.foot_positions_history['right']) < 5:
            return 50.0  # Недостаточно данных

        total_repositions = 0
        total_stable_positions = 0
        total_pivots = 0

        for side in ['left', 'right']:
            positions = [(p[0], p[1]) for p in self.foot_positions_history[side]]
            angles = self.foot_angle_history[side]
            if len(positions) < 5 or len(angles) != len(positions):
                continue

            repositions, pivots, stable = self._count_repositions_with_rotation_filter(
                foot_positions=positions,
                foot_angles=angles,
                threshold=self.POSITION_THRESHOLD,
            )
            total_repositions += repositions
            total_pivots += pivots
            total_stable_positions += stable
            self._log_quiet_feet_debug(side, repositions, pivots, stable)

        if total_stable_positions == 0:
            return 50.0

        avg_repositions = total_repositions / total_stable_positions

        # Шкала оценки
        if avg_repositions < 1.5:
            score = 90 + (1.5 - avg_repositions) * 6.67  # 90-100%
        elif avg_repositions < 2.5:
            score = 70 + (2.5 - avg_repositions) * 19  # 70-89%
        elif avg_repositions < 4.0:
            score = 50 + (4.0 - avg_repositions) * 13.33  # 50-69%
        else:
            score = max(0, 50 - (avg_repositions - 4.0) * 12.5)  # 0-49%
        
        # Ритм не должен падать до 0 при шуме
        return max(20.0, min(100.0, score))

    def _calc_foot_angle(self, landmarks, foot_side: str) -> float:
        """Угол стопы по вектору пятка->носок."""
        if foot_side == 'left':
            heel_idx, toe_idx = 29, 31
        else:
            heel_idx, toe_idx = 30, 32

        if len(landmarks) <= max(heel_idx, toe_idx):
            return 0.0

        heel = landmarks[heel_idx]
        toe = landmarks[toe_idx]
        if heel.visibility < 0.5 or toe.visibility < 0.5:
            return 0.0

        dx = toe.x - heel.x
        dy = toe.y - heel.y
        angle = math.degrees(math.atan2(dy, dx))
        return angle % 360

    def _is_pivot(self, prev_angle: float, curr_angle: float) -> bool:
        """Пивот: существенный поворот стопы в той же зоне опоры."""
        angle_diff = abs(curr_angle - prev_angle)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        return angle_diff >= self.ROTATION_THRESHOLD_DEG

    def _count_repositions_with_rotation_filter(
        self,
        foot_positions: List[Tuple[float, float]],
        foot_angles: List[float],
        threshold: float,
    ) -> Tuple[int, int, int]:
        """
        Считает перестановки с фильтром пивотов.
        Возвращает: (repositions, pivots, stable_positions)
        """
        clusters: List[Dict[str, Any]] = []
        total_repositions = 0
        total_pivots = 0
        total_stable = 0

        for pos, angle in zip(foot_positions, foot_angles):
            matched_cluster = None

            for cluster in clusters:
                cx, cy = cluster['center']
                dist = math.sqrt((pos[0] - cx) ** 2 + (pos[1] - cy) ** 2)
                if dist < threshold:
                    matched_cluster = cluster
                    break

            if matched_cluster is None:
                clusters.append({
                    'center': pos,
                    'last_angle': angle,
                    'count': 1,
                })
                total_stable += 1
                continue

            if self._is_pivot(matched_cluster['last_angle'], angle):
                total_pivots += 1
            else:
                total_repositions += 1

            matched_cluster['last_angle'] = angle
            matched_cluster['count'] += 1

        return total_repositions, total_pivots, total_stable

    def _log_quiet_feet_debug(self, side: str, repositions: int, pivots: int, stable: int) -> None:
        total_events = repositions + pivots
        pivot_pct = (pivots / total_events * 100) if total_events > 0 else 0
        logger.info(
            f"QuietFeet [{side}]: repositions={repositions}, pivots={pivots} "
            f"({pivot_pct:.0f}% filtered), stable_positions={stable}, "
            f"avg_repositions={repositions / max(stable, 1):.2f}"
        )
    
    def _calculate_hip_position(self, landmarks) -> float:
        """
        Hip Position (Положение таза)
        Угол отклонения линии плечи-таз от вертикали
        """
        try:
            left_hip = landmarks.landmark[23] if len(landmarks.landmark) > 23 else None
            right_hip = landmarks.landmark[24] if len(landmarks.landmark) > 24 else None
            left_shoulder = landmarks.landmark[11] if len(landmarks.landmark) > 11 else None
            right_shoulder = landmarks.landmark[12] if len(landmarks.landmark) > 12 else None
            
            if not all([left_hip, right_hip, left_shoulder, right_shoulder]):
                return 50.0
            
            if any([lm.visibility < 0.5 for lm in [left_hip, right_hip, left_shoulder, right_shoulder]]):
                return 50.0
            
            # Центр таза
            hip_center = (
                (left_hip.x + right_hip.x) / 2,
                (left_hip.y + right_hip.y) / 2,
                (left_hip.z + right_hip.z) / 2 if hasattr(left_hip, 'z') else 0
            )
            
            # Центр плеч
            shoulder_center = (
                (left_shoulder.x + right_shoulder.x) / 2,
                (left_shoulder.y + right_shoulder.y) / 2,
                (left_shoulder.z + right_shoulder.z) / 2 if hasattr(left_shoulder, 'z') else 0
            )
            
            # Вектор от таза к плечам
            dx = shoulder_center[0] - hip_center[0]
            dy = shoulder_center[1] - hip_center[1]
            
            # Угол с вертикалью (ось Y направлена вверх)
            vertical = (0, -1)
            body_vector = (dx, dy)
            
            # Нормализуем векторы
            body_len = math.sqrt(dx**2 + dy**2)
            if body_len == 0:
                return 50.0
            
            body_vector_norm = (dx / body_len, dy / body_len)
            
            # Угол между векторами (в радианах)
            dot_product = body_vector_norm[0] * vertical[0] + body_vector_norm[1] * vertical[1]
            angle_rad = math.acos(max(-1, min(1, dot_product)))
            angle_deg = math.degrees(angle_rad)
            
            # Учитываем глубину (Z координата)
            if hasattr(left_hip, 'z') and hasattr(left_shoulder, 'z'):
                depth_diff = abs(hip_center[2] - shoulder_center[2])
                if depth_diff > 0.05:  # Таз дальше от стены
                    angle_deg += depth_diff * 100
            
            # Шкала оценки
            if angle_deg < 10:
                score = 90 + (10 - angle_deg) * 1.0  # 90-100%
            elif angle_deg < 20:
                score = 70 + (20 - angle_deg) * 1.9  # 70-89%
            elif angle_deg < 35:
                score = 50 + (35 - angle_deg) * 1.33  # 50-69%
            else:
                score = max(0, 50 - (angle_deg - 35) * 2.86)  # 0-49%
            
            return max(0.0, min(100.0, score))
        except Exception as e:
            logger.warning(f"Ошибка расчета hip_position: {e}")
            return 50.0
    
    def _calculate_diagonal_coordination(self) -> float:
        """
        Противовес (Diagonal Movement)
        Корреляция движений противоположных конечностей
        """
        if len(self.hand_positions_history['left']) < 5 or len(self.hand_positions_history['right']) < 5:
            return 50.0
        
        if len(self.foot_positions_history['left']) < 5 or len(self.foot_positions_history['right']) < 5:
            return 50.0
        
        # Вычисляем движения за последние N кадров
        window_size = min(30, len(self.hand_positions_history['left']))
        
        # Движения рук и ног
        left_hand_movements = []
        right_hand_movements = []
        left_foot_movements = []
        right_foot_movements = []
        
        # Левая рука
        for i in range(1, min(window_size, len(self.hand_positions_history['left']))):
            prev = self.hand_positions_history['left'][-i-1]
            curr = self.hand_positions_history['left'][-i]
            dist = math.sqrt((curr[0] - prev[0])**2 + (curr[1] - prev[1])**2)
            left_hand_movements.append(dist)
        
        # Правая рука
        for i in range(1, min(window_size, len(self.hand_positions_history['right']))):
            prev = self.hand_positions_history['right'][-i-1]
            curr = self.hand_positions_history['right'][-i]
            dist = math.sqrt((curr[0] - prev[0])**2 + (curr[1] - prev[1])**2)
            right_hand_movements.append(dist)
        
        # Левая нога
        for i in range(1, min(window_size, len(self.foot_positions_history['left']))):
            prev = self.foot_positions_history['left'][-i-1]
            curr = self.foot_positions_history['left'][-i]
            dist = math.sqrt((curr[0] - prev[0])**2 + (curr[1] - prev[1])**2)
            left_foot_movements.append(dist)
        
        # Правая нога
        for i in range(1, min(window_size, len(self.foot_positions_history['right']))):
            prev = self.foot_positions_history['right'][-i-1]
            curr = self.foot_positions_history['right'][-i]
            dist = math.sqrt((curr[0] - prev[0])**2 + (curr[1] - prev[1])**2)
            right_foot_movements.append(dist)
        
        # Нормализуем длины
        min_len = min(
            len(left_hand_movements),
            len(right_hand_movements),
            len(left_foot_movements),
            len(right_foot_movements)
        )
        
        if min_len < 3:
            return 50.0
        
        left_hand_movements = left_hand_movements[:min_len]
        right_hand_movements = right_hand_movements[:min_len]
        left_foot_movements = left_foot_movements[:min_len]
        right_foot_movements = right_foot_movements[:min_len]
        
        # Корреляция: правая рука ↔ левая нога
        corr_1 = self._correlation(right_hand_movements, left_foot_movements)
        
        # Корреляция: левая рука ↔ правая нога
        corr_2 = self._correlation(left_hand_movements, right_foot_movements)
        
        avg_correlation = (corr_1 + corr_2) / 2
        
        # Шкала оценки
        if avg_correlation > 0.8:
            score = 90 + (avg_correlation - 0.8) * 50  # 90-100%
        elif avg_correlation > 0.6:
            score = 70 + (avg_correlation - 0.6) * 100  # 70-89%
        elif avg_correlation > 0.4:
            score = 50 + (avg_correlation - 0.4) * 100  # 50-69%
        elif avg_correlation > 0.1:
            score = 30 + (avg_correlation - 0.1) * 66.67  # 30-49%
        else:
            # Если корреляция очень низкая или отрицательная, но есть движения — это статика
            # Статика не означает плохую диагональ, это нормально для некоторых стилей
            score = 60.0  # Дефолт для статики
        
        return max(10.0, min(100.0, score))  # Минимум 10%, НИКОГДА 0%
    
    def _correlation(self, x: List[float], y: List[float]) -> float:
        """Вычисление корреляции Пирсона"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        sum_sq_x = sum((x[i] - mean_x) ** 2 for i in range(n))
        sum_sq_y = sum((y[i] - mean_y) ** 2 for i in range(n))
        
        denominator = math.sqrt(sum_sq_x * sum_sq_y)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _calculate_route_reading(self, timestamp: float) -> float:
        """
        Считывание (Route Reading)
        Паузы для просмотра маршрута
        """
        # Время до первого движения
        if self.route_reading_data['first_movement_time'] is None:
            if len(self.hand_positions_history['left']) > 1 or len(self.hand_positions_history['right']) > 1:
                self.route_reading_data['first_movement_time'] = timestamp
        
        # Определяем паузы взгляда (короткие остановки 1-3 сек с поднятой головой)
        # Упрощенная версия: паузы между движениями > 1 сек
        if len(self.movement_intervals) > 0:
            for interval in self.movement_intervals:
                if 1.0 <= interval / 1000 <= 3.0:  # 1-3 секунды
                    self.route_reading_data['reading_pauses'].append(interval)
                    if len(self.route_reading_data['reading_pauses']) > 10:
                        self.route_reading_data['reading_pauses'].pop(0)
        
        # Оценка
        start_time = self.route_reading_data.get('first_movement_time', 2.0)  # Дефолт 2 сек
        reading_pauses_count = len(self.route_reading_data.get('reading_pauses', []))
        
        # Время до старта (до 5 сек = хорошо)
        if start_time is None or start_time == 0:
            start_time = 2.0  # Дефолт если данных нет
        start_score = min(start_time / 5.0, 1.0) * 50
        
        # Количество пауз (3+ паузы = хорошо)
        pause_score = min(reading_pauses_count / 3.0, 1.0) * 50
        
        total_score = start_score + pause_score
        
        # Если оба показателя низкие, даём минимум 20% (не 0%)
        if total_score < 20:
            total_score = 20.0
        
        return max(20.0, min(100.0, total_score))  # Минимум 20%, НИКОГДА 0%
    
    def _calculate_rhythm_stability(self) -> float:
        """
        Ритм (Movement Rhythm)
        Стабильность интервалов между движениями
        """
        if len(self.movement_intervals) < 3:
            return 100.0  # Недостаточно данных
        
        intervals = np.array(self.movement_intervals)
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        
        if mean_interval == 0:
            return 50.0
        
        # Коэффициент вариации (CV)
        cv = std_interval / mean_interval
        
        # Преобразуем в балл (CV < 0.2 = отлично, CV > 0.5 = плохо)
        # score = max(0, min(100, (1 - cv * 2) * 100))
        
        # Более точная шкала на основе разброса в мс
        if std_interval <= 100:
            score = 90 + (100 - std_interval) * 0.1  # 90-100%
        elif std_interval <= 200:
            score = 70 + (200 - std_interval) * 0.2  # 70-89%
        elif std_interval <= 350:
            score = 50 + (350 - std_interval) * 0.133  # 50-69%
        else:
            score = max(0, 50 - (std_interval - 350) * 0.143)  # 0-49%
        
        return max(0.0, min(100.0, score))
    
    def _calculate_dynamic_control(self) -> float:
        """
        Контроль динамики (Dynamic Control)
        Качество выполнения динамических движений (бросков)
        """
        # Упрощенная версия: анализируем быстрые движения рук
        if len(self.hand_positions_history['left']) < 5 and len(self.hand_positions_history['right']) < 5:
            return 100.0  # Нет динамики — нет проблем
        
        scores = []
        window = 5
        
        for side in ['left', 'right']:
            positions = self.hand_positions_history[side]
            if len(positions) < window * 2:
                continue
            
            # Ищем быстрые движения (динамические ходы)
            for i in range(window, len(positions) - window):
                prev = positions[i - window]
                curr = positions[i]
                next_pos = positions[i + window]
                
                # Скорость движения
                velocity = math.sqrt(
                    (curr[0] - prev[0])**2 + (curr[1] - prev[1])**2
                ) / (window * 0.033)  # Предполагаем 30 FPS
                
                # Если движение быстрое (> threshold), это динамический ход
                if velocity > 0.05:  # Порог для динамики
                    # Время стабилизации после движения
                    stabilization_time = window * 0.033  # Упрощенно
                    
                    # Отклонение от целевой точки (упрощенно)
                    landing_deviation = math.sqrt(
                        (next_pos[0] - curr[0])**2 + (next_pos[1] - curr[1])**2
                    )
                    
                    # Оценка стабилизации (< 500мс = отлично)
                    stab_score = max(0, 100 - (stabilization_time * 1000 - 300) / 5) if stabilization_time * 1000 > 300 else 100
                    
                    # Оценка точности (< 30px = отлично, но у нас нормализованные координаты)
                    acc_score = max(0, 100 - landing_deviation * 2000)  # Масштабируем
                    
                    scores.append((stab_score + acc_score) / 2)
        
        if len(scores) == 0:
            return 100.0  # Нет динамических движений
        
        avg_score = sum(scores) / len(scores)
        
        # Шкала оценки
        if avg_score >= 90:
            return 90 + (avg_score - 90) * 1.0  # 90-100%
        elif avg_score >= 70:
            return 70 + (avg_score - 70) * 0.95  # 70-89%
        elif avg_score >= 50:
            return 50 + (avg_score - 50) * 1.0  # 50-69%
        else:
            return max(0, avg_score * 1.0)  # 0-49%
    
    def _calculate_grip_release(self) -> float:
        """
        Grip Release (Мягкость перехватов)
        Плавность отпускания зацепов
        """
        if len(self.hand_positions_history['left']) < 10 and len(self.hand_positions_history['right']) < 10:
            return 50.0
        
        smoothness_scores = []
        
        for side in ['left', 'right']:
            positions = self.hand_positions_history[side]
            if len(positions) < 10:
                continue
            
            # Анализируем траектории при перехватах (быстрые движения вверх)
            for i in range(5, len(positions) - 5):
                # Участок траектории при отпускании (первые 200мс = ~6 кадров при 30 FPS)
                release_segment = positions[max(0, i-6):i+1]
                
                if len(release_segment) < 3:
                    continue
                
                # Вычисляем ускорения (вторая производная)
                accelerations = []
                for j in range(1, len(release_segment) - 1):
                    prev = release_segment[j-1]
                    curr = release_segment[j]
                    next_pos = release_segment[j+1]
                    
                    # Скорости
                    v1 = math.sqrt((curr[0] - prev[0])**2 + (curr[1] - prev[1])**2)
                    v2 = math.sqrt((next_pos[0] - curr[0])**2 + (next_pos[1] - curr[1])**2)
                    
                    # Ускорение (изменение скорости)
                    accel = abs(v2 - v1)
                    accelerations.append(accel)
                
                if len(accelerations) == 0:
                    continue
                
                # Резкие пики ускорения = рывки
                threshold = 0.01  # Порог для рывка
                jerk_count = sum(1 for accel in accelerations if accel > threshold)
                
                # Плавность = отсутствие рывков
                score = max(0, 100 - jerk_count * 20)
                smoothness_scores.append(score)
        
        if len(smoothness_scores) == 0:
            return 50.0
        
        avg_score = sum(smoothness_scores) / len(smoothness_scores)
        
        # Шкала оценки
        if avg_score >= 90:
            return 90 + (avg_score - 90) * 1.0  # 90-100%
        elif avg_score >= 70:
            return 70 + (avg_score - 70) * 0.95  # 70-89%
        elif avg_score >= 50:
            return 50 + (avg_score - 50) * 1.0  # 50-69%
        else:
            return max(0, avg_score * 1.02)  # 0-49%
    
    def _get_default_metrics(self) -> Dict[str, float]:
        """Возвращает метрики по умолчанию"""
        return {
            'quiet_feet': 50.0,
            'hip_position': 50.0,
            'diagonal': 50.0,
            'route_reading': 50.0,
            'rhythm': 50.0,
            'dynamic_control': 50.0,
            'grip_release': 50.0
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Возвращает сводку по всем метрикам
        
        Returns:
            dict с метриками и дополнительной информацией
        """
        # Вычисляем текущие метрики
        metrics = self._get_default_metrics()
        
        # Если есть история, вычисляем средние значения
        if len(self.foot_positions_history['left']) > 5:
            # Упрощенно возвращаем дефолтные значения
            # В реальной реализации здесь нужно пересчитать метрики на основе всей истории
            pass
        
        return {
            'metrics': metrics,
            'foot_positions_count': {
                'left': len(self.foot_positions_history['left']),
                'right': len(self.foot_positions_history['right'])
            },
            'hand_positions_count': {
                'left': len(self.hand_positions_history['left']),
                'right': len(self.hand_positions_history['right'])
            },
            'movement_intervals_count': len(self.movement_intervals),
            'hand_moves_count': self.hand_moves_count,
            'dynamic_moves_count': self.dynamic_moves_count,
            'max_reach_ratio': self.max_reach_ratio
        }
