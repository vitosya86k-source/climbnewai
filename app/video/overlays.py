"""
ClimbAI BoulderVision - Система визуализации v3.0

5 ключевых визуализаций для скалолазания:

1. spider_metrics  - Паутинка: Сила/Баланс/Координация/Уровень (на русском)
2. weight_load     - Нагрузка в КГ на каждую конечность
3. ideal_ghost     - Призрак-эталон (идеальный вариант, опережает)
4. tension_zones   - Зажимы и зоны риска травм
5. speed_map       - Скорость перемещения и карта решений

Принципы:
- Клёвая визуализация для соцсетей
- Короткий, лаконичный профиль
- Данные для предиктивной аналитики
"""

import cv2
import numpy as np
import mediapipe as mp
from typing import Dict, Any, List, Tuple, Optional
import logging
import math

logger = logging.getLogger(__name__)


class VideoOverlays:
    """
    Система визуализации ClimbAI v3.0

    5 типов:
    - spider_metrics: паутинка метрик
    - weight_load: нагрузка в КГ
    - ideal_ghost: призрак-эталон
    - tension_zones: зажимы/травмы
    - speed_map: скорость движения
    """

    def __init__(self, user_weight_kg: float = 70.0):
        self.mp_pose = mp.solutions.pose
        self.mp_draw = mp.solutions.drawing_utils

        # Вес пользователя для расчёта нагрузки
        self.user_weight_kg = user_weight_kg

        # История для анализа
        self.metrics_history: List[Dict[str, float]] = []
        self.position_history: List[Dict[str, Tuple[float, float]]] = []
        self.tension_history: List[Dict[str, float]] = []
        self.max_history = 90  # 3 секунды при 30fps

        # Для призрака-эталона
        self.ideal_landmarks_sequence: List[Any] = []
        self.current_frame_idx: int = 0

        # Для скорости
        self.velocity_history: List[float] = []
        self.decision_points: List[Tuple[float, float, float]] = []
        
        # Новые метрики техники (7 базовых)
        self.technique_metrics_history: List[Dict[str, float]] = []
        self.additional_metrics_history: List[Dict[str, float]] = []

    def reset(self):
        """Сброс всех историй"""
        self.metrics_history.clear()
        self.position_history.clear()
        self.tension_history.clear()
        self.velocity_history.clear()
        self.decision_points.clear()
        self.current_frame_idx = 0
        self.technique_metrics_history.clear()
        self.additional_metrics_history.clear()

    def set_user_weight(self, weight_kg: float):
        """Установить вес пользователя"""
        self.user_weight_kg = max(30.0, min(200.0, weight_kg))

    def set_ideal_sequence(self, landmarks_sequence: List[Any]):
        """Загрузить идеальную последовательность для призрака"""
        self.ideal_landmarks_sequence = landmarks_sequence

    def load_ghost_from_file(self, ghost_name: str) -> bool:
        """
        Загрузить эталон из файла через GhostManager

        Args:
            ghost_name: имя эталона (без .json)

        Returns:
            bool: успешность загрузки
        """
        try:
            from .ghost_manager import load_ghost_for_overlay
            landmarks = load_ghost_for_overlay(ghost_name)
            if landmarks:
                self.ideal_landmarks_sequence = landmarks
                logger.info(f"Эталон '{ghost_name}' загружен: {len(landmarks)} кадров")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка загрузки эталона: {e}")
            return False

    def has_ghost_loaded(self) -> bool:
        """Проверить, загружен ли эталон"""
        return bool(self.ideal_landmarks_sequence)

    def apply_overlay(
        self,
        frame: np.ndarray,
        landmarks,
        overlay_type: str,
        frame_data: Dict[str, Any],
        holds_detector=None,
        holds: List = None
    ) -> np.ndarray:
        """
        Применить визуализацию к кадру

        Args:
            frame: исходный кадр
            landmarks: MediaPipe landmarks
            overlay_type: тип визуализации
            frame_data: данные анализа кадра
        """
        # Обновляем историю
        if landmarks:
            self._update_history(landmarks, frame.shape[:2], frame_data)

        # Выбираем тип визуализации
        if overlay_type == "spider_metrics":
            return self.draw_spider_metrics(frame, landmarks, frame_data)

        elif overlay_type == "weight_load":
            return self.draw_weight_load(frame, landmarks, frame_data)

        elif overlay_type == "ideal_ghost":
            return self.draw_ideal_ghost(frame, landmarks, frame_data)

        elif overlay_type == "tension_zones":
            return self.draw_tension_zones(frame, landmarks, frame_data)

        elif overlay_type == "speed_map":
            return self.draw_speed_map(frame, landmarks, frame_data)

        elif overlay_type == "full":
            # Комбинированный режим - все метрики на одном видео
            return self.draw_full_analysis(frame, landmarks, frame_data)

        else:
            logger.warning(f"Неизвестный тип overlay: {overlay_type}, использую full")
            return self.draw_full_analysis(frame, landmarks, frame_data)

    def _update_history(self, landmarks, frame_shape: Tuple[int, int], frame_data: Dict):
        """Обновить историю для всех типов анализа"""
        h, w = frame_shape

        # Позиции ключевых точек
        positions = {}
        if landmarks:
            key_points = {
                'left_wrist': 15, 'right_wrist': 16,
                'left_ankle': 27, 'right_ankle': 28,
                'left_hip': 23, 'right_hip': 24,
                'nose': 0
            }

            for name, idx in key_points.items():
                if idx < len(landmarks.landmark):
                    lm = landmarks.landmark[idx]
                    if lm.visibility > 0.5:  # Только видимые точки
                        positions[name] = (lm.x, lm.y)

        self.position_history.append(positions)
        if len(self.position_history) > self.max_history:
            self.position_history.pop(0)

        # Метрики - ВСЕГДА вычисляем, даже если landmarks None
        metrics = self._calculate_current_metrics(landmarks, frame_data)
        # Убеждаемся, что все значения валидны
        validated_metrics = {}
        for key, value in metrics.items():
            if value is None or (isinstance(value, float) and math.isnan(value)):
                validated_metrics[key] = 50.0
            else:
                validated_metrics[key] = max(0.0, min(100.0, float(value)))
        self.metrics_history.append(validated_metrics)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history.pop(0)

        # Напряжение
        tension = self._calculate_tension(landmarks, frame_data)
        self.tension_history.append(tension)
        if len(self.tension_history) > self.max_history:
            self.tension_history.pop(0)

        # Скорость
        if len(self.position_history) >= 2:
            velocity = self._calculate_velocity()
            self.velocity_history.append(velocity)
            if len(self.velocity_history) > self.max_history:
                self.velocity_history.pop(0)

        self.current_frame_idx += 1

    def _calculate_current_metrics(self, landmarks, frame_data: Dict) -> Dict[str, float]:
        """Рассчитать текущие метрики для паутинки"""
        # Сила (на основе углов рук и позы)
        strength = self._calculate_strength(landmarks) if landmarks else 50.0

        # Баланс (на основе центра масс и позиции)
        balance = self._calculate_balance(landmarks) if landmarks else 50.0

        # Координация (на основе синхронности движений)
        coordination = self._calculate_coordination(landmarks) if landmarks else 50.0

        # Уровень/Техника (общая оценка)
        technique = self._calculate_technique(landmarks, frame_data) if landmarks else 50.0

        # Убеждаемся, что все значения валидны
        return {
            'сила': max(0.0, min(100.0, float(strength) if strength is not None else 50.0)),
            'баланс': max(0.0, min(100.0, float(balance) if balance is not None else 50.0)),
            'координация': max(0.0, min(100.0, float(coordination) if coordination is not None else 50.0)),
            'техника': max(0.0, min(100.0, float(technique) if technique is not None else 50.0))
        }

    def _calculate_strength(self, landmarks) -> float:
        """Оценка силы на основе углов суставов"""
        try:
            # Угол в локтях - чем меньше, тем больше нагрузка
            left_elbow = self._get_angle(landmarks, 11, 13, 15)  # плечо-локоть-запястье
            right_elbow = self._get_angle(landmarks, 12, 14, 16)

            # Оптимальный угол локтя 90-120 градусов
            left_score = 100 - abs(105 - left_elbow) * 0.8 if left_elbow else 50
            right_score = 100 - abs(105 - right_elbow) * 0.8 if right_elbow else 50

            strength = (left_score + right_score) / 2
            return max(0, min(100, strength))
        except:
            return 50.0

    def _calculate_balance(self, landmarks) -> float:
        """Оценка баланса"""
        try:
            # Центр масс относительно базы поддержки
            left_hip = landmarks.landmark[23]
            right_hip = landmarks.landmark[24]
            left_ankle = landmarks.landmark[27]
            right_ankle = landmarks.landmark[28]

            # Центр бёдер
            hip_center_x = (left_hip.x + right_hip.x) / 2

            # Центр ног (база поддержки)
            ankle_center_x = (left_ankle.x + right_ankle.x) / 2

            # Отклонение от вертикали
            deviation = abs(hip_center_x - ankle_center_x)

            # Чем меньше отклонение, тем лучше баланс
            balance = 100 - deviation * 500
            return max(0, min(100, balance))
        except:
            return 50.0

    def _calculate_coordination(self, landmarks) -> float:
        """Оценка координации на основе симметрии движений"""
        try:
            if len(self.position_history) < 5:
                return 50.0

            # Сравниваем движения левой и правой стороны
            recent = self.position_history[-5:]

            left_movement = 0
            right_movement = 0

            for i in range(1, len(recent)):
                if 'left_wrist' in recent[i] and 'left_wrist' in recent[i-1]:
                    dx = recent[i]['left_wrist'][0] - recent[i-1]['left_wrist'][0]
                    dy = recent[i]['left_wrist'][1] - recent[i-1]['left_wrist'][1]
                    left_movement += math.sqrt(dx**2 + dy**2)

                if 'right_wrist' in recent[i] and 'right_wrist' in recent[i-1]:
                    dx = recent[i]['right_wrist'][0] - recent[i-1]['right_wrist'][0]
                    dy = recent[i]['right_wrist'][1] - recent[i-1]['right_wrist'][1]
                    right_movement += math.sqrt(dx**2 + dy**2)

            # Симметрия движений
            if left_movement + right_movement > 0:
                symmetry = 1 - abs(left_movement - right_movement) / (left_movement + right_movement + 0.001)
            else:
                symmetry = 1.0

            coordination = symmetry * 100
            return max(0, min(100, coordination))
        except:
            return 50.0

    def _calculate_technique(self, landmarks, frame_data: Dict) -> float:
        """Общая оценка техники"""
        try:
            pose_quality = frame_data.get('pose_quality', 50)
            motion = frame_data.get('motion_intensity', 50)

            # Хорошая техника: высокое качество позы, умеренное движение
            technique = pose_quality * 0.6 + (100 - abs(motion - 40)) * 0.4
            return max(0, min(100, technique))
        except:
            return 50.0

    def _calculate_tension(self, landmarks, frame_data: Dict) -> Dict[str, float]:
        """Рассчитать напряжение в разных зонах"""
        tension = {
            'левое_плечо': 0,
            'правое_плечо': 0,
            'левый_локоть': 0,
            'правый_локоть': 0,
            'поясница': 0,
            'левое_колено': 0,
            'правое_колено': 0
        }

        try:
            # Плечи - угол отведения
            left_shoulder_angle = self._get_angle(landmarks, 23, 11, 13)
            right_shoulder_angle = self._get_angle(landmarks, 24, 12, 14)

            if left_shoulder_angle:
                # Напряжение растёт при углах >120 или <30
                tension['левое_плечо'] = self._angle_to_tension(left_shoulder_angle, 60, 120)

            if right_shoulder_angle:
                tension['правое_плечо'] = self._angle_to_tension(right_shoulder_angle, 60, 120)

            # Локти
            left_elbow = self._get_angle(landmarks, 11, 13, 15)
            right_elbow = self._get_angle(landmarks, 12, 14, 16)

            if left_elbow:
                tension['левый_локоть'] = self._angle_to_tension(left_elbow, 80, 150)

            if right_elbow:
                tension['правый_локоть'] = self._angle_to_tension(right_elbow, 80, 150)

            # Поясница - угол наклона корпуса
            spine_angle = self._get_spine_angle(landmarks)
            if spine_angle:
                tension['поясница'] = self._angle_to_tension(spine_angle, 160, 180)

            # Колени
            left_knee = self._get_angle(landmarks, 23, 25, 27)
            right_knee = self._get_angle(landmarks, 24, 26, 28)

            if left_knee:
                tension['левое_колено'] = self._angle_to_tension(left_knee, 90, 170)

            if right_knee:
                tension['правое_колено'] = self._angle_to_tension(right_knee, 90, 170)

        except Exception as e:
            logger.debug(f"Ошибка расчёта напряжения: {e}")

        return tension

    def _angle_to_tension(self, angle: float, optimal_min: float, optimal_max: float) -> float:
        """Преобразовать угол в уровень напряжения (0-100)"""
        if optimal_min <= angle <= optimal_max:
            return 0  # В оптимальной зоне

        if angle < optimal_min:
            deviation = optimal_min - angle
        else:
            deviation = angle - optimal_max

        # Напряжение растёт с отклонением
        tension = min(100, deviation * 2)
        return tension

    def _calculate_velocity(self) -> float:
        """Рассчитать скорость движения"""
        if len(self.position_history) < 2:
            return 0.0

        prev = self.position_history[-2]
        curr = self.position_history[-1]

        total_movement = 0
        count = 0

        for key in ['left_wrist', 'right_wrist', 'nose']:
            if key in prev and key in curr:
                dx = curr[key][0] - prev[key][0]
                dy = curr[key][1] - prev[key][1]
                total_movement += math.sqrt(dx**2 + dy**2)
                count += 1

        return total_movement / max(1, count)

    def _get_angle(self, landmarks, p1_idx: int, p2_idx: int, p3_idx: int) -> Optional[float]:
        """Получить угол между тремя точками"""
        try:
            p1 = landmarks.landmark[p1_idx]
            p2 = landmarks.landmark[p2_idx]
            p3 = landmarks.landmark[p3_idx]

            # Проверяем видимость
            if p1.visibility < 0.5 or p2.visibility < 0.5 or p3.visibility < 0.5:
                return None

            # Векторы
            v1 = (p1.x - p2.x, p1.y - p2.y)
            v2 = (p3.x - p2.x, p3.y - p2.y)

            # Угол
            dot = v1[0]*v2[0] + v1[1]*v2[1]
            mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
            mag2 = math.sqrt(v2[0]**2 + v2[1]**2)

            if mag1 * mag2 == 0:
                return None

            cos_angle = dot / (mag1 * mag2)
            cos_angle = max(-1, min(1, cos_angle))
            angle = math.degrees(math.acos(cos_angle))

            return angle
        except:
            return None

    def _get_spine_angle(self, landmarks) -> Optional[float]:
        """Получить угол наклона позвоночника"""
        try:
            # Используем плечи и бёдра
            left_shoulder = landmarks.landmark[11]
            right_shoulder = landmarks.landmark[12]
            left_hip = landmarks.landmark[23]
            right_hip = landmarks.landmark[24]

            # Центры
            shoulder_center = ((left_shoulder.x + right_shoulder.x) / 2,
                             (left_shoulder.y + right_shoulder.y) / 2)
            hip_center = ((left_hip.x + right_hip.x) / 2,
                         (left_hip.y + right_hip.y) / 2)

            # Угол от вертикали
            dx = shoulder_center[0] - hip_center[0]
            dy = shoulder_center[1] - hip_center[1]

            angle = math.degrees(math.atan2(abs(dx), abs(dy)))
            return 180 - angle  # Инвертируем для понятности
        except:
            return None

    # ========== ВИЗУАЛИЗАЦИИ ==========

    def draw_spider_metrics(self, frame: np.ndarray, landmarks, frame_data: Dict) -> np.ndarray:
        """
        1. ПАУТИНКА МЕТРИК
        Radar chart: Сила, Баланс, Координация, Техника
        """
        h, w = frame.shape[:2]
        result = frame.copy()

        # Рисуем полупрозрачный скелет
        if landmarks:
            self._draw_skeleton_light(result, landmarks)

        # Получаем метрики - ПРИОРИТЕТ НОВЫМ МЕТРИКАМ ТЕХНИКИ
        metrics = {}
        
        # Сначала пытаемся использовать новые метрики техники (7 базовых)
        if self.technique_metrics_history:
            latest_technique = self.technique_metrics_history[-1]
            metrics = latest_technique.copy()
        # Fallback на старые метрики для обратной совместимости
        elif self.metrics_history:
            metrics = self.metrics_history[-1]
        else:
            # Дефолтные значения для новых метрик
            metrics = {
                'quiet_feet': 50.0, 'hip_position': 50.0, 'diagonal': 50.0,
                'route_reading': 50.0, 'rhythm': 50.0, 'dynamic_control': 50.0, 'grip_release': 50.0
            }
        
        # Валидация метрик
        validated_metrics = {}
        for key, val in metrics.items():
            if val is None or (isinstance(val, float) and math.isnan(val)):
                val = 50.0
            validated_metrics[key] = max(0.0, min(100.0, float(val)))
        metrics = validated_metrics
        
        # #region agent log
        with open('/home/user/с винды/ClimbAI/telegram_bot_bouldervision/.cursor/debug.log', 'a') as f:
            import json
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"overlays.py:475","message":"metrics after validation","data":{"validated_metrics":validated_metrics},"timestamp":int(__import__('time').time()*1000)})+'\n')
        # #endregion

        # Параметры паутинки
        center_x = w - 150
        center_y = 150
        radius = 100

        # НОВАЯ КОНЦЕПЦИЯ: 7 базовых метрик техники
        categories = ['QF', 'HP', 'ПВ', 'СЧ', 'РТ', 'ДН', 'GR']
        category_names = ['Quiet Feet', 'Hip Position', 'Противовес', 'Считывание', 'Ритм', 'Динамика', 'Grip Release']
        keys = ['quiet_feet', 'hip_position', 'diagonal', 'route_reading', 'rhythm', 'dynamic_control', 'grip_release']
        colors = [
            (0, 255, 100),   # Зелёный - Quiet Feet
            (100, 200, 255), # Голубой - Hip Position
            (255, 200, 0),   # Жёлтый - Противовес
            (200, 100, 255), # Фиолетовый - Считывание
            (255, 150, 0),   # Оранжевый - Ритм
            (0, 200, 255),   # Циан - Динамика
            (255, 100, 100)  # Красноватый - Grip Release
        ]
        
        # Если новые метрики не доступны, используем старые (для обратной совместимости)
        if not any(key in metrics for key in keys):
            categories = ['Сила', 'Баланс', 'Координация', 'Техника']
            category_names = categories
            keys = ['сила', 'баланс', 'координация', 'техника']
            colors = [
                (0, 100, 255),   # Оранжевый - сила
                (0, 255, 0),     # Зелёный - баланс
                (255, 255, 0),   # Голубой - координация
                (255, 0, 255)    # Пурпурный - техника
            ]

        # Фон для паутинки
        overlay = result.copy()
        cv2.circle(overlay, (center_x, center_y), radius + 20, (0, 0, 0), -1)
        cv2.addWeighted(result, 0.7, overlay, 0.3, 0, result)

        # Концентрические круги
        for r in [0.25, 0.5, 0.75, 1.0]:
            cv2.circle(result, (center_x, center_y), int(radius * r), (60, 60, 60), 1)

        # Оси и точки
        num_axes = len(categories)
        angle_step = 360 / num_axes
        points = []

        for i, (cat, key, color) in enumerate(zip(categories, keys, colors)):
            angle = math.radians(i * angle_step - 90)

            # Линия оси
            end_x = int(center_x + radius * math.cos(angle))
            end_y = int(center_y + radius * math.sin(angle))
            cv2.line(result, (center_x, center_y), (end_x, end_y), (80, 80, 80), 1)

            # Подпись
            label_x = int(center_x + (radius + 25) * math.cos(angle))
            label_y = int(center_y + (radius + 25) * math.sin(angle))

            # Центрируем текст (используем короткие названия для компактности)
            text_size = cv2.getTextSize(cat, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
            cv2.putText(result, cat, (label_x - text_size[0]//2, label_y + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

            # Точка значения (убеждаемся, что значение валидно)
            value_raw = metrics.get(key, 50)
            if value_raw is None or math.isnan(value_raw):
                value_raw = 50.0
            value_raw = max(0.0, min(100.0, float(value_raw)))
            value = value_raw / 100.0
            
            point_x = int(center_x + radius * value * math.cos(angle))
            point_y = int(center_y + radius * value * math.sin(angle))
            points.append((point_x, point_y))

            # Значение рядом с точкой (исправлено форматирование)
            value_text = f"{int(value_raw)}"
            text_size_val = cv2.getTextSize(value_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
            # Фон для значения
            cv2.rectangle(result, (point_x + 5 - 2, point_y - text_size_val[1] - 5 - 2),
                         (point_x + 5 + text_size_val[0] + 2, point_y - 5 + 2), (0, 0, 0), -1)
            cv2.putText(result, value_text,
                       (point_x + 5, point_y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)

        # Заполненный многоугольник
        if len(points) >= 3:
            pts = np.array(points, np.int32).reshape((-1, 1, 2))

            # Заливка
            overlay = result.copy()
            cv2.fillPoly(overlay, [pts], (100, 150, 255))
            cv2.addWeighted(result, 0.6, overlay, 0.4, 0, result)

            # Обводка
            cv2.polylines(result, [pts], True, (255, 255, 255), 2)

            # Точки
            for i, (px, py) in enumerate(points):
                cv2.circle(result, (px, py), 5, colors[i], -1)
                cv2.circle(result, (px, py), 6, (255, 255, 255), 1)

        # Заголовок
        cv2.putText(result, "МЕТРИКИ", (center_x - 40, center_y - radius - 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

        # Средний балл (исправлено вычисление)
        valid_values = [v for v in metrics.values() if isinstance(v, (int, float)) and not math.isnan(v)]
        if valid_values:
            avg_score = sum(valid_values) / len(valid_values)
        else:
            avg_score = 50.0
        avg_score = max(0.0, min(100.0, float(avg_score)))
        cv2.putText(result, f"Общий: {int(avg_score)}%", (center_x - 35, center_y + radius + 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        return result

    def draw_weight_load(self, frame: np.ndarray, landmarks, frame_data: Dict) -> np.ndarray:
        """
        2. НАГРУЗКА В КГ
        Показывает распределение веса на конечности
        """
        h, w = frame.shape[:2]
        result = frame.copy()

        if not landmarks:
            return result

        # Рисуем скелет
        self._draw_skeleton_light(result, landmarks)

        # Рассчитываем распределение веса
        weight_distribution = self._calculate_weight_distribution(landmarks)
        
        # #region agent log
        with open('/home/user/с винды/ClimbAI/telegram_bot_bouldervision/.cursor/debug.log', 'a') as f:
            import json
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"overlays.py:596","message":"weight_distribution calculated","data":{"weight_distribution":weight_distribution},"timestamp":int(__import__('time').time()*1000)})+'\n')
        # #endregion

        # Точки для отображения нагрузки
        limb_points = {
            'Л.рука': (15, weight_distribution.get('left_arm', 0)),
            'П.рука': (16, weight_distribution.get('right_arm', 0)),
            'Л.нога': (27, weight_distribution.get('left_leg', 0)),
            'П.нога': (28, weight_distribution.get('right_leg', 0))
        }

        for name, (idx, load_percent) in limb_points.items():
            # #region agent log
            with open('/home/user/с винды/ClimbAI/telegram_bot_bouldervision/.cursor/debug.log', 'a') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"overlays.py:607","message":"load_percent value","data":{"name":name,"idx":idx,"load_percent":load_percent,"is_none":load_percent is None,"is_nan":isinstance(load_percent,float) and math.isnan(load_percent)},"timestamp":int(__import__('time').time()*1000)})+'\n')
            # #endregion
            if idx >= len(landmarks.landmark):
                continue

            lm = landmarks.landmark[idx]
            if lm.visibility < 0.5:
                continue

            x = int(lm.x * w)
            y = int(lm.y * h)

            # Вес в кг
            load_kg = self.user_weight_kg * load_percent / 100

            # Цвет по нагрузке
            if load_percent < 20:
                color = (0, 255, 0)      # Зелёный - мало
            elif load_percent < 35:
                color = (0, 255, 255)    # Жёлтый - норма
            elif load_percent < 50:
                color = (0, 165, 255)    # Оранжевый - много
            else:
                color = (0, 0, 255)      # Красный - перегрузка

            # Размер круга пропорционален нагрузке
            radius = int(15 + load_percent * 0.4)

            # Полупрозрачный круг
            overlay = result.copy()
            cv2.circle(overlay, (x, y), radius, color, -1)
            cv2.addWeighted(result, 0.6, overlay, 0.4, 0, result)

            # Обводка
            cv2.circle(result, (x, y), radius, (255, 255, 255), 2)

            # Текст ТОЛЬКО с процентом (без кг, так как вес неизвестен)
            # Валидация load_percent
            if load_percent is None or (isinstance(load_percent, float) and math.isnan(load_percent)):
                load_percent = 0.0
            load_percent = max(0.0, min(100.0, float(load_percent)))
            
            # #region agent log
            with open('/home/user/с винды/ClimbAI/telegram_bot_bouldervision/.cursor/debug.log', 'a') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"overlays.py:644","message":"text formatting","data":{"load_percent":load_percent,"text_before_format":f"{load_percent:.1f}%"},"timestamp":int(__import__('time').time()*1000)})+'\n')
            # #endregion
            
            text = f"{load_percent:.1f}%"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]

            # Позиция текста
            text_x = x - text_size[0] // 2
            text_y = y - radius - 10

            # Фон для текста
            cv2.rectangle(result, (text_x - 3, text_y - text_size[1] - 3),
                         (text_x + text_size[0] + 3, text_y + 3), (0, 0, 0), -1)
            cv2.putText(result, text, (text_x, text_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)

            # Название конечности
            cv2.putText(result, name, (x - 20, y + radius + 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1, cv2.LINE_AA)

        # Заголовок (без веса, так как он неизвестен)
        cv2.putText(result, "НАГРУЗКА (%)", (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        # Легенда
        legend_y = h - 80
        cv2.putText(result, "Нагрузка:", (20, legend_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        for i, (label, color) in enumerate([("Мало", (0, 255, 0)), ("Норма", (0, 255, 255)),
                                            ("Много", (0, 165, 255)), ("Опасно", (0, 0, 255))]):
            cv2.circle(result, (30 + i * 70, legend_y + 20), 6, color, -1)
            cv2.putText(result, label, (40 + i * 70, legend_y + 24),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)

        return result

    def _calculate_weight_distribution(self, landmarks) -> Dict[str, float]:
        """Рассчитать распределение веса по конечностям"""
        distribution = {
            'left_arm': 0,
            'right_arm': 0,
            'left_leg': 0,
            'right_leg': 0
        }

        try:
            # Получаем позиции
            left_wrist = landmarks.landmark[15]
            right_wrist = landmarks.landmark[16]
            left_ankle = landmarks.landmark[27]
            right_ankle = landmarks.landmark[28]
            left_hip = landmarks.landmark[23]
            right_hip = landmarks.landmark[24]

            # Центр бёдер (приблизительный центр масс)
            hip_y = (left_hip.y + right_hip.y) / 2

            # Распределение веса зависит от высоты конечностей относительно ЦМ
            # и углов суставов

            # Руки берут больше веса, если они выше ЦМ и согнуты
            left_arm_height = hip_y - left_wrist.y
            right_arm_height = hip_y - right_wrist.y

            # Ноги берут больше веса, если они ниже и опираются
            left_leg_support = left_ankle.y - hip_y
            right_leg_support = right_ankle.y - hip_y

            # Нормализуем
            total = abs(left_arm_height) + abs(right_arm_height) + \
                    abs(left_leg_support) + abs(right_leg_support) + 0.001

            # Базовое распределение
            distribution['left_arm'] = max(5, min(50, abs(left_arm_height) / total * 100 * 1.5))
            distribution['right_arm'] = max(5, min(50, abs(right_arm_height) / total * 100 * 1.5))
            distribution['left_leg'] = max(5, min(50, abs(left_leg_support) / total * 100 * 1.2))
            distribution['right_leg'] = max(5, min(50, abs(right_leg_support) / total * 100 * 1.2))

            # Нормализуем до 100%
            current_total = sum(distribution.values())
            if current_total > 0:
                for key in distribution:
                    distribution[key] = distribution[key] / current_total * 100

        except Exception as e:
            logger.debug(f"Ошибка расчёта веса: {e}")
            # Равномерное распределение по умолчанию
            distribution = {'left_arm': 25, 'right_arm': 25, 'left_leg': 25, 'right_leg': 25}

        return distribution

    def draw_ideal_ghost(self, frame: np.ndarray, landmarks, frame_data: Dict) -> np.ndarray:
        """
        3. ПРИЗРАК-ЭТАЛОН
        Идеальный вариант выполнения (опережает текущего)
        """
        h, w = frame.shape[:2]
        result = frame.copy()

        # #region agent log
        with open('/home/user/с винды/ClimbAI/telegram_bot_bouldervision/.cursor/debug.log', 'a') as f:
            import json
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"overlays.py:742","message":"ideal_ghost check","data":{"has_ideal_sequence":bool(self.ideal_landmarks_sequence),"ideal_sequence_len":len(self.ideal_landmarks_sequence) if self.ideal_landmarks_sequence else 0},"timestamp":int(__import__('time').time()*1000)})+'\n')
        # #endregion
        
        # Если нет идеальной последовательности - показываем только текущего
        # с подсказкой
        if not self.ideal_landmarks_sequence:
            # Рисуем текущего скалолаза
            if landmarks:
                self._draw_skeleton_colored(result, landmarks, (0, 255, 0), "ТЕКУЩИЙ")

            cv2.putText(result, "ПРИЗРАК-ЭТАЛОН", (20, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(result, "Загрузите эталонное видео для сравнения", (20, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1, cv2.LINE_AA)
            return result

        # Индекс призрака (опережает на 10 кадров)
        ghost_idx = min(self.current_frame_idx + 10, len(self.ideal_landmarks_sequence) - 1)

        if ghost_idx < len(self.ideal_landmarks_sequence):
            ghost_landmarks = self.ideal_landmarks_sequence[ghost_idx]

            # Рисуем призрак (полупрозрачный, синий)
            self._draw_ghost_skeleton(result, ghost_landmarks, (255, 150, 100))

        # Рисуем текущего (зелёный)
        if landmarks:
            self._draw_skeleton_colored(result, landmarks, (0, 255, 0), None)

        # Заголовок
        cv2.putText(result, "ПРИЗРАК-ЭТАЛОН", (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        # Легенда
        cv2.circle(result, (30, h - 40), 8, (0, 255, 0), -1)
        cv2.putText(result, "Ты", (45, h - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.circle(result, (90, h - 40), 8, (255, 150, 100), -1)
        cv2.putText(result, "Эталон", (105, h - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        return result

    def draw_tension_zones(self, frame: np.ndarray, landmarks, frame_data: Dict) -> np.ndarray:
        """
        4. ЗАЖИМЫ И ЗОНЫ РИСКА
        Показывает где перенапряжение и риск травм
        """
        h, w = frame.shape[:2]
        result = frame.copy()

        if not landmarks:
            return result

        # Получаем текущее напряжение
        if self.tension_history:
            tension = self.tension_history[-1]
        else:
            tension = self._calculate_tension(landmarks, frame_data)

        # Точки суставов для отображения
        joint_points = {
            'левое_плечо': 11,
            'правое_плечо': 12,
            'левый_локоть': 13,
            'правый_локоть': 14,
            'поясница': 23,  # Используем левое бедро как приблизительную точку
            'левое_колено': 25,
            'правое_колено': 26
        }

        # Сначала рисуем базовый скелет
        self._draw_skeleton_light(result, landmarks)

        # Накладываем зоны напряжения
        warnings = []

        for zone_name, joint_idx in joint_points.items():
            if joint_idx >= len(landmarks.landmark):
                continue

            lm = landmarks.landmark[joint_idx]
            if lm.visibility < 0.5:
                continue

            x = int(lm.x * w)
            y = int(lm.y * h)

            tension_level = tension.get(zone_name, 0)

            # Цвет по уровню напряжения
            if tension_level < 20:
                color = (0, 255, 0)      # Зелёный - норма
                status = "ОК"
            elif tension_level < 50:
                color = (0, 255, 255)    # Жёлтый - внимание
                status = "!"
            elif tension_level < 75:
                color = (0, 165, 255)    # Оранжевый - зажим
                status = "ЗАЖИМ"
                warnings.append(f"{zone_name}: зажим")
            else:
                color = (0, 0, 255)      # Красный - опасно
                status = "ОПАСНО"
                warnings.append(f"{zone_name}: РИСК ТРАВМЫ!")

            # Размер индикатора
            radius = int(10 + tension_level * 0.3)

            # Пульсирующий эффект для высокого напряжения
            if tension_level > 50:
                pulse = int(5 * math.sin(self.current_frame_idx * 0.3))
                radius += pulse

            # Рисуем индикатор
            overlay = result.copy()
            cv2.circle(overlay, (x, y), radius, color, -1)
            cv2.addWeighted(result, 0.5, overlay, 0.5, 0, result)
            cv2.circle(result, (x, y), radius, (255, 255, 255), 2)

            # Статус
            if tension_level > 30:
                cv2.putText(result, status, (x - 15, y - radius - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)

        # Заголовок
        cv2.putText(result, "ЗАЖИМЫ И РИСКИ", (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        # Предупреждения
        if warnings:
            y_pos = 70
            for warning in warnings[:3]:  # Максимум 3
                cv2.putText(result, f"⚠ {warning}", (20, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1, cv2.LINE_AA)
                y_pos += 20
        else:
            cv2.putText(result, "✓ Все зоны в норме", (20, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)

        # Легенда
        legend_y = h - 60
        for i, (label, color) in enumerate([("Норма", (0, 255, 0)), ("Внимание", (0, 255, 255)),
                                            ("Зажим", (0, 165, 255)), ("Опасно", (0, 0, 255))]):
            cv2.circle(result, (30 + i * 80, legend_y), 6, color, -1)
            cv2.putText(result, label, (40 + i * 80, legend_y + 4),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)

        return result

    def draw_speed_map(self, frame: np.ndarray, landmarks, frame_data: Dict) -> np.ndarray:
        """
        5. СКОРОСТЬ И КАРТА РЕШЕНИЙ
        Показывает скорость перемещения и моменты остановок
        """
        h, w = frame.shape[:2]
        result = frame.copy()

        # Рисуем скелет
        if landmarks:
            self._draw_skeleton_light(result, landmarks)

        # Текущая скорость
        current_velocity = self.velocity_history[-1] if self.velocity_history else 0

        # Определяем момент раздумий (низкая скорость)
        if current_velocity < 0.005 and landmarks:
            # Добавляем точку раздумий
            nose = landmarks.landmark[0]
            if nose.visibility > 0.5:
                existing = False
                for i, (px, py, dur) in enumerate(self.decision_points):
                    if abs(px - nose.x) < 0.05 and abs(py - nose.y) < 0.05:
                        self.decision_points[i] = (px, py, dur + 1)
                        existing = True
                        break
                if not existing:
                    self.decision_points.append((nose.x, nose.y, 1))

        # Рисуем точки раздумий
        for x_norm, y_norm, duration in self.decision_points[-20:]:
            x = int(x_norm * w)
            y = int(y_norm * h)

            # Размер и цвет зависят от длительности
            if duration < 10:
                color = (0, 255, 0)
                radius = 15
            elif duration < 30:
                color = (0, 255, 255)
                radius = 20
            elif duration < 60:
                color = (0, 165, 255)
                radius = 25
            else:
                color = (0, 0, 255)
                radius = 30

            # Полупрозрачный круг
            overlay = result.copy()
            cv2.circle(overlay, (x, y), radius, color, -1)
            cv2.addWeighted(result, 0.7, overlay, 0.3, 0, result)
            cv2.circle(result, (x, y), radius, (255, 255, 255), 2)

            # Время в секундах
            seconds = duration / 30  # при 30fps
            if seconds >= 0.5:
                cv2.putText(result, f"{seconds:.1f}с", (x - 15, y + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

        # Индикатор текущей скорости (спидометр)
        speed_x = w - 100
        speed_y = 100

        # Фон спидометра
        cv2.circle(result, (speed_x, speed_y), 50, (30, 30, 30), -1)
        cv2.circle(result, (speed_x, speed_y), 50, (100, 100, 100), 2)

        # Стрелка скорости (исправлено - правильный расчет угла)
        # Нормализуем скорость от 0 до 1
        speed_normalized = min(1.0, max(0.0, current_velocity * 100))  # Увеличиваем множитель для лучшей чувствительности
        
        # Спидометр: от -90 (низ) до +90 (верх) градусов
        # -90 градусов = 0 скорости (вниз)
        # 0 градусов = средняя скорость (вправо)
        # +90 градусов = максимальная скорость (вверх)
        angle_degrees = -90 + speed_normalized * 180
        angle = math.radians(angle_degrees)

        # Длина стрелки
        arrow_length = 35
        arrow_x = int(speed_x + arrow_length * math.cos(angle))
        arrow_y = int(speed_y + arrow_length * math.sin(angle))

        # Рисуем стрелку
        cv2.line(result, (speed_x, speed_y), (arrow_x, arrow_y), (0, 255, 255), 3)
        
        # Наконечник стрелки (треугольник)
        arrow_tip_size = 8
        tip_angle1 = angle + math.radians(150)
        tip_angle2 = angle - math.radians(150)
        tip1_x = int(arrow_x + arrow_tip_size * math.cos(tip_angle1))
        tip1_y = int(arrow_y + arrow_tip_size * math.sin(tip_angle1))
        tip2_x = int(arrow_x + arrow_tip_size * math.cos(tip_angle2))
        tip2_y = int(arrow_y + arrow_tip_size * math.sin(tip_angle2))
        cv2.fillPoly(result, [np.array([[arrow_x, arrow_y], [tip1_x, tip1_y], [tip2_x, tip2_y]])], (0, 255, 255))
        
        # Центр спидометра
        cv2.circle(result, (speed_x, speed_y), 5, (255, 255, 255), -1)

        # Метка скорости
        speed_text = "БЫСТРО" if speed_normalized > 0.6 else "СРЕДНЕ" if speed_normalized > 0.3 else "МЕДЛЕННО"
        cv2.putText(result, speed_text, (speed_x - 30, speed_y + 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

        # Заголовок
        cv2.putText(result, "СКОРОСТЬ И РЕШЕНИЯ", (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        # Легенда
        cv2.putText(result, "Остановки:", (20, h - 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        for i, (label, color) in enumerate([("<0.5с", (0, 255, 0)), ("0.5-1с", (0, 255, 255)),
                                            ("1-2с", (0, 165, 255)), (">2с", (0, 0, 255))]):
            cv2.circle(result, (30 + i * 70, h - 25), 6, color, -1)
            cv2.putText(result, label, (40 + i * 70, h - 21),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 200, 200), 1)

        return result

    def draw_full_analysis(self, frame: np.ndarray, landmarks, frame_data: Dict) -> np.ndarray:
        """
        ПОЛНЫЙ АНАЛИЗ - все метрики на одном видео
        Компактное размещение для соцсетей
        """
        h, w = frame.shape[:2]
        result = frame.copy()

        # #region agent log
        with open('/home/user/с винды/ClimbAI/telegram_bot_bouldervision/.cursor/debug.log', 'a') as f:
            import json
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"overlays.py:1000","message":"draw_full_analysis called","data":{"has_landmarks":landmarks is not None,"metrics_history_len":len(self.metrics_history),"tension_history_len":len(self.tension_history),"velocity_history_len":len(self.velocity_history)},"timestamp":int(__import__('time').time()*1000)})+'\n')
        # #endregion

        if not landmarks:
            # Если нет landmarks, показываем сообщение
            cv2.putText(result, "Нет данных о позе", (w//2 - 100, h//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            return result

        # Убеждаемся, что история метрик обновлена (ПРИОРИТЕТ НОВЫМ МЕТРИКАМ)
        if not self.technique_metrics_history and not self.metrics_history:
            # Вычисляем метрики сейчас, если их нет
            metrics = self._calculate_current_metrics(landmarks, frame_data)
            self.metrics_history.append(metrics)

        # НОВАЯ КОНЦЕПЦИЯ: Кружочки напряжения + паутинка + показатели нагрузки
        
        # Рисуем кружочки с напряжением на ключевых точках
        self._draw_skeleton_with_tension(result, landmarks)
        
        # === ПРАВЫЙ ВЕРХНИЙ УГОЛ: Паутинка с 7 метриками техники ===
        spider_center_x = w - 120  # Правый верхний угол
        spider_center_y = 120  # Отступ сверху
        
        # === НИЖНИЙ ЛЕВЫЙ УГОЛ: Показатели нагрузки ===
        self._draw_load_indicators(result, landmarks, frame_data)
        
        # ВСЕГДА используем новые метрики техники (7 осей)
        if self.technique_metrics_history:
            # #region agent log
            with open('/home/user/с винды/ClimbAI/telegram_bot_bouldervision/.cursor/debug.log', 'a') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"overlays.py:1105","message":"draw_full_analysis using new spider","data":{"technique_metrics_count":len(self.technique_metrics_history)},"timestamp":int(__import__('time').time()*1000)})+'\n')
            # #endregion
            self._draw_mini_spider_new(result, spider_center_x, spider_center_y)
            # Вычисляем avg_score из новых метрик
            metrics = self.technique_metrics_history[-1]
            valid_values = [v for v in metrics.values() if isinstance(v, (int, float)) and not math.isnan(v)]
            if valid_values:
                avg_score = sum(valid_values) / len(valid_values)
            else:
                avg_score = 50.0
        else:
            # #region agent log
            with open('/home/user/с винды/ClimbAI/telegram_bot_bouldervision/.cursor/debug.log', 'a') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"overlays.py:1110","message":"draw_full_analysis fallback to old spider","data":{"metrics_history_count":len(self.metrics_history)},"timestamp":int(__import__('time').time()*1000)})+'\n')
            # #endregion
            # Fallback на старую паутинку если новых метрик нет (тоже в верхнем левом углу)
            self._draw_mini_spider(result, spider_center_x, spider_center_y)
            # Вычисляем avg_score из старых метрик
            if self.metrics_history:
                metrics = self.metrics_history[-1]
                valid_values = [v for v in metrics.values() if isinstance(v, (int, float)) and not math.isnan(v)]
                if valid_values:
                    avg_score = sum(valid_values) / len(valid_values)
                else:
                    avg_score = 50.0
            else:
                avg_score = 50.0

        # УБРАНО: Качество пролаза внизу (знаки вопросов и %)
        # Оставляем только лого
        cv2.putText(result, "ClimbAI", (w - 80, h - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1, cv2.LINE_AA)

        return result

    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========

    def _draw_skeleton_light(self, frame: np.ndarray, landmarks):
        """Нарисовать полупрозрачный скелет"""
        self.mp_draw.draw_landmarks(
            frame, landmarks, self.mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=self.mp_draw.DrawingSpec(color=(150, 150, 150), thickness=2, circle_radius=3),
            connection_drawing_spec=self.mp_draw.DrawingSpec(color=(100, 100, 100), thickness=2)
        )

    def _draw_skeleton_colored(self, frame: np.ndarray, landmarks, color: Tuple[int, int, int], label: str = None):
        """Нарисовать скелет определённого цвета"""
        self.mp_draw.draw_landmarks(
            frame, landmarks, self.mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=self.mp_draw.DrawingSpec(color=color, thickness=3, circle_radius=4),
            connection_drawing_spec=self.mp_draw.DrawingSpec(color=color, thickness=2)
        )
        if label:
            h, w = frame.shape[:2]
            cv2.putText(frame, label, (w - 100, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)

    def _draw_ghost_skeleton(self, frame: np.ndarray, landmarks_data: List[Dict], color: Tuple[int, int, int]):
        """Нарисовать призрак (полупрозрачный)"""
        h, w = frame.shape[:2]
        overlay = frame.copy()

        # Соединения MediaPipe Pose
        connections = [
            (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
            (11, 23), (12, 24), (23, 24),
            (23, 25), (25, 27), (24, 26), (26, 28)
        ]

        for start_idx, end_idx in connections:
            if start_idx < len(landmarks_data) and end_idx < len(landmarks_data):
                start = landmarks_data[start_idx]
                end = landmarks_data[end_idx]

                if start.get('visibility', 0) > 0.5 and end.get('visibility', 0) > 0.5:
                    start_pt = (int(start['x'] * w), int(start['y'] * h))
                    end_pt = (int(end['x'] * w), int(end['y'] * h))
                    cv2.line(overlay, start_pt, end_pt, color, 2)

        # Точки
        for lm in landmarks_data:
            if lm.get('visibility', 0) > 0.5:
                pt = (int(lm['x'] * w), int(lm['y'] * h))
                cv2.circle(overlay, pt, 4, color, -1)

        cv2.addWeighted(frame, 0.7, overlay, 0.3, 0, frame)

    def _draw_skeleton_with_tension(self, frame: np.ndarray, landmarks):
        """
        Рисует КРУЖОЧКИ с напряжением на ключевых точках тела (НОВАЯ ВЕРСИЯ).
        Без линий скелета - только цветные кружочки с процентами напряжения.
        """
        h, w = frame.shape[:2]

        if self.tension_history:
            tension = self.tension_history[-1]
        else:
            tension = {}

        # Ключевые точки для отображения кружочков с напряжением
        # (индекс MediaPipe, ключ напряжения, смещение текста x, y)
        key_points = [
            (11, 'левое_плечо', 0, -5),      # Левое плечо
            (12, 'правое_плечо', 0, -5),     # Правое плечо
            (13, 'левый_локоть', 0, 0),      # Левый локоть
            (14, 'правый_локоть', 0, 0),     # Правый локоть
            (15, 'левое_запястье', 0, 0),    # Левое запястье
            (16, 'правое_запястье', 0, 0),   # Правое запястье
            (23, 'левое_бедро', 0, 0),       # Левое бедро
            (24, 'правое_бедро', 0, 0),      # Правое бедро
            (25, 'левое_колено', 0, 0),      # Левое колено
            (26, 'правое_колено', 0, 0),     # Правое колено
            (27, 'левая_лодыжка', 0, 5),     # Левая лодыжка
            (28, 'правая_лодыжка', 0, 5),    # Правая лодыжка
        ]
        
        # Рисуем кружочки с напряжением на каждой ключевой точке
        for idx, tension_key, offset_x, offset_y in key_points:
            if idx >= len(landmarks.landmark):
                continue
            
            lm = landmarks.landmark[idx]
            if lm.visibility < 0.5:
                continue
            
            x, y = int(lm.x * w), int(lm.y * h)
            
            # Получаем напряжение для этой зоны
            t = tension.get(tension_key, 50)
            if t is None or (isinstance(t, float) and math.isnan(t)):
                t = 50
            t = max(0, min(100, int(t)))
            
            # Определяем цвет и размер кружочка
            color = self._tension_to_color(t)
            circle_radius = 22  # Размер кружочка
            
            # Рисуем кружочек с заливкой
            overlay = frame.copy()
            cv2.circle(overlay, (x, y), circle_radius, color, -1)
            cv2.addWeighted(frame, 0.3, overlay, 0.7, 0, frame)
            
            # Обводка кружочка
            cv2.circle(frame, (x, y), circle_radius, (255, 255, 255), 2)
            
            # УБРАНО: цифры внутри кружочков (по запросу пользователя)
    
    def _draw_load_indicators(self, frame: np.ndarray, landmarks, frame_data: Dict):
        """
        Рисует показатели в нижнем левом углу:
        - Стабильность (дрожание/микрокоррекции)
        - Продуктивность (эффект/затраты)
        - Экономичность (минимум лишних движений)
        - Баланс (центр масс относительно опоры)
        """
        h, w = frame.shape[:2]
        
        # Получаем данные из additional_metrics_history или вычисляем
        if self.additional_metrics_history:
            add_metrics = self.additional_metrics_history[-1]
        else:
            add_metrics = {}
        
        # Получаем значения (с дефолтами)
        stability = add_metrics.get('stability', 50)
        productivity = add_metrics.get('productivity', 50)
        economy = add_metrics.get('economy', 50)
        balance = add_metrics.get('balance', 50)
        
        # Валидация
        for val in [stability, productivity, economy, balance]:
            if val is None or (isinstance(val, float) and math.isnan(val)):
                val = 50
        
        stability = max(0, min(100, int(stability)))
        productivity = max(0, min(100, int(productivity)))
        economy = max(0, min(100, int(economy)))
        balance = max(0, min(100, int(balance)))
        
        # Позиция: нижний левый угол (смещено вправо от левого края, без подложки)
        start_x = 50  # Смещено вправо от левого края (было 8)
        start_y = h - 75
        line_height = 20  # Увеличено расстояние между строками
        
        # Текст (полные надписи, увеличен размер, уменьшена толщина)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5  # Увеличено с 0.45
        
        indicators = [
            (f"Stability: {stability}%", self._get_indicator_color(stability)),
            (f"Productivity: {productivity}%", self._get_indicator_color(productivity)),
            (f"Economy: {economy}%", self._get_indicator_color(economy)),
            (f"Balance: {balance}%", self._get_indicator_color(balance)),
        ]
        
        for i, (text, color) in enumerate(indicators):
            y = start_y + i * line_height
            # Тень для читаемости (тоньше)
            cv2.putText(frame, text, (start_x + 1, y + 1), font, font_scale, (0, 0, 0), 1, cv2.LINE_AA)
            cv2.putText(frame, text, (start_x, y), font, font_scale, color, 1, cv2.LINE_AA)  # Толщина 1 вместо 2
    
    def _get_indicator_color(self, value: float) -> Tuple[int, int, int]:
        """Цвет для индикатора по значению (BGR)"""
        if value >= 70:
            return (0, 255, 0)  # Зелёный
        elif value >= 50:
            return (0, 255, 255)  # Жёлтый
        elif value >= 30:
            return (0, 165, 255)  # Оранжевый
        else:
            return (0, 0, 255)  # Красный
    
    def _tension_to_color(self, tension: float) -> Tuple[int, int, int]:
        """
        Преобразование уровня напряжения в цвет (BGR)
        
        Args:
            tension: уровень напряжения 0-100
            
        Returns:
            (B, G, R) цвет в BGR формате для OpenCV
        """
        tension = max(0.0, min(100.0, float(tension)))
        
        if tension < 30:
            # Зелёный — норма (BGR)
            return (0, 255, 0)
        elif tension < 60:
            # Жёлтый — внимание (BGR: B=0, G=255, R=255)
            return (0, 255, 255)
        elif tension < 80:
            # Оранжевый — повышенное напряжение (BGR: B=0, G=165, R=255)
            return (0, 165, 255)
        else:
            # Красный — зажим (BGR: B=0, G=0, R=255)
            return (0, 0, 255)

    def _draw_mini_spider(self, frame: np.ndarray, cx: int, cy: int):
        """Нарисовать мини-паутинку метрик"""
        if not self.metrics_history:
            # Если нет истории, используем дефолтные значения
            metrics = {'сила': 50, 'баланс': 50, 'координация': 50, 'техника': 50}
        else:
            metrics = self.metrics_history[-1]
            # Убеждаемся, что все значения валидны
            metrics = {
                'сила': max(0.0, min(100.0, float(metrics.get('сила', 50)) if metrics.get('сила') is not None else 50.0)),
                'баланс': max(0.0, min(100.0, float(metrics.get('баланс', 50)) if metrics.get('баланс') is not None else 50.0)),
                'координация': max(0.0, min(100.0, float(metrics.get('координация', 50)) if metrics.get('координация') is not None else 50.0)),
                'техника': max(0.0, min(100.0, float(metrics.get('техника', 50)) if metrics.get('техника') is not None else 50.0))
            }
        
        radius = 50

        # Фон
        overlay = frame.copy()
        cv2.circle(overlay, (cx, cy), radius + 10, (0, 0, 0), -1)
        cv2.addWeighted(frame, 0.6, overlay, 0.4, 0, frame)

        # Круги
        for r in [0.5, 1.0]:
            cv2.circle(frame, (cx, cy), int(radius * r), (60, 60, 60), 1)

        # Оси и точки (ASCII для корректного отображения)
        categories = ['S', 'B', 'C', 'T']  # Strength, Balance, Coordination, Technique
        keys = ['сила', 'баланс', 'координация', 'техника']
        colors = [(0, 100, 255), (0, 255, 0), (255, 255, 0), (255, 0, 255)]
        points = []

        for i, (cat, key, color) in enumerate(zip(categories, keys, colors)):
            angle = math.radians(i * 90 - 90)

            # Ось
            end_x = int(cx + radius * math.cos(angle))
            end_y = int(cy + radius * math.sin(angle))
            cv2.line(frame, (cx, cy), (end_x, end_y), (60, 60, 60), 1)

            # Метка
            label_x = int(cx + (radius + 15) * math.cos(angle))
            label_y = int(cy + (radius + 15) * math.sin(angle))
            cv2.putText(frame, cat, (label_x - 5, label_y + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)

            # Точка (нормализуем значение от 0 до 1)
            value_raw = metrics.get(key, 50)
            value = max(0.0, min(1.0, float(value_raw) / 100.0))
            px = int(cx + radius * value * math.cos(angle))
            py = int(cy + radius * value * math.sin(angle))
            points.append((px, py))
            
            # Значение рядом с точкой
            value_text = f"{int(value_raw)}"
            cv2.putText(frame, value_text, (px + 3, py - 3),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1, cv2.LINE_AA)

        # Многоугольник
        if len(points) >= 3:
            pts = np.array(points, np.int32).reshape((-1, 1, 2))
            cv2.fillPoly(frame, [pts], (100, 150, 255))
            cv2.polylines(frame, [pts], True, (255, 255, 255), 1)
            
            # Точки на вершинах
            for px, py in points:
                cv2.circle(frame, (px, py), 3, (255, 255, 255), -1)

    def _draw_mini_spider_new(self, frame: np.ndarray, cx: int, cy: int):
        """Нарисовать паутинку с НОВЫМИ 7 метриками техники (УВЕЛИЧЕННАЯ)"""
        if not self.technique_metrics_history:
            # Fallback на старую паутинку
            # #region agent log
            with open('/home/user/с винды/ClimbAI/telegram_bot_bouldervision/.cursor/debug.log', 'a') as f:
                import json as _json
                f.write(_json.dumps({"sessionId":"debug-session","runId":"run2","hypothesisId":"H-B","location":"overlays.py:_draw_mini_spider_new:fallback","message":"No technique_metrics_history, using fallback","data":{"technique_metrics_history_len":0},"timestamp":int(__import__('time').time()*1000)})+'\n')
            # #endregion
            self._draw_mini_spider(frame, cx, cy)
            return
        
        metrics = self.technique_metrics_history[-1]
        
        # Валидация всех 7 метрик
        metric_keys = ['quiet_feet', 'hip_position', 'diagonal', 'route_reading', 'rhythm', 'dynamic_control', 'grip_release']
        validated = {}
        for key in metric_keys:
            val = metrics.get(key, 50.0)
            if val is None or (isinstance(val, float) and math.isnan(val)):
                val = 50.0
            validated[key] = max(0.0, min(100.0, float(val)))
        metrics = validated
        
        # #region agent log
        with open('/home/user/с винды/ClimbAI/telegram_bot_bouldervision/.cursor/debug.log', 'a') as f:
            import json as _json
            f.write(_json.dumps({"sessionId":"debug-session","runId":"run2","hypothesisId":"H-B","location":"overlays.py:_draw_mini_spider_new:metrics","message":"Spider metrics values","data":{"metrics":metrics,"cx":cx,"cy":cy},"timestamp":int(__import__('time').time()*1000)})+'\n')
        # #endregion
        
        # === КОНФИГУРАЦИЯ (увеличено и смещено вправо) ===
        radius = 55  # Увеличено для лучшей видимости
        
        # Фон (тёмный круг)
        overlay = frame.copy()
        cv2.circle(overlay, (cx, cy), radius + 15, (30, 30, 30), -1)
        cv2.addWeighted(frame, 0.15, overlay, 0.85, 0, frame)
        
        # === КРУГИ ШКАЛЫ (25%, 50%, 75%, 100%) ===
        for pct in [25, 50, 75, 100]:
            r = int(radius * pct / 100)
            cv2.circle(frame, (cx, cy), r, (60, 60, 60), 1)
        
        # === 7 ОСЕЙ (только ASCII для корректного отображения в OpenCV) ===
        categories = ['QF', 'HP', 'DM', 'RR', 'RT', 'DC', 'GR']
        # QF=Quiet Feet, HP=Hip Position, DM=Diagonal Move, RR=Route Reading, RT=Rhythm, DC=Dynamic Control, GR=Grip Release
        keys = metric_keys
        colors = [
            (0, 255, 100),   # QF - зелёный
            (100, 200, 255), # HP - голубой
            (255, 200, 0),   # DM - жёлтый
            (200, 100, 255), # RR - фиолетовый
            (255, 150, 0),   # RT - оранжевый
            (0, 200, 255),   # DC - циан
            (255, 100, 100)  # GR - красноватый
        ]
        points = []
        
        num_axes = 7
        angle_step = 2 * math.pi / num_axes
        
        for i, (cat, key, color) in enumerate(zip(categories, keys, colors)):
            angle = -math.pi/2 + i * angle_step  # Начинаем сверху
            
            # Ось
            end_x = int(cx + radius * math.cos(angle))
            end_y = int(cy + radius * math.sin(angle))
            cv2.line(frame, (cx, cy), (end_x, end_y), (80, 80, 80), 1)
            
            # Подпись оси (СНАРУЖИ паутинки) - увеличено расстояние для "Диагональная координация"
            label_distance = 35  # Увеличено с 30 для предотвращения обрезания текста
            label_x = int(cx + label_distance * math.cos(angle))
            label_y = int(cy + label_distance * math.sin(angle))
            # Фон для букв для читаемости
            (text_w, text_h), baseline = cv2.getTextSize(cat, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(frame, (label_x - text_w//2 - 3, label_y - text_h - 3), 
                         (label_x + text_w//2 + 3, label_y + 3), (0, 0, 0), -1)
            cv2.putText(frame, cat, (label_x - text_w//2, label_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
            
            # Точка значения
            val = metrics.get(key, 50.0)
            point_r = radius * val / 100
            point_x = int(cx + point_r * math.cos(angle))
            point_y = int(cy + point_r * math.sin(angle))
            points.append((point_x, point_y))
        
        # === ЗАПОЛНЕННЫЙ ПОЛИГОН ===
        if len(points) >= 3:
            pts = np.array(points, np.int32).reshape((-1, 1, 2))
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], (255, 200, 0))  # Жёлто-оранжевый
            cv2.addWeighted(frame, 0.7, overlay, 0.3, 0, frame)
            cv2.polylines(frame, [pts], True, (255, 255, 255), 2)
        
        # === ТОЧКИ НА ВЕРШИНАХ ===
        for point in points:
            cv2.circle(frame, point, 5, (255, 255, 255), -1)
        
                # УБРАНО: Score (по запросу пользователя)

    def _draw_weight_labels(self, frame: np.ndarray, landmarks, weight_dist: Dict):
        """Нарисовать метки веса у конечностей"""
        h, w = frame.shape[:2]

        points = {
            'left_arm': (15, 'Л'),
            'right_arm': (16, 'П'),
            'left_leg': (27, 'Л'),
            'right_leg': (28, 'П')
        }

        for key, (idx, prefix) in points.items():
            if idx >= len(landmarks.landmark):
                continue

            lm = landmarks.landmark[idx]
            if lm.visibility < 0.5:
                continue

            x, y = int(lm.x * w), int(lm.y * h)
            load = weight_dist.get(key, 25)
            # Убеждаемся, что load валиден
            if load is None or (isinstance(load, float) and math.isnan(load)):
                load = 25.0
            load = max(0.0, min(100.0, float(load)))

            # Цвет по нагрузке
            color = (0, 255, 0) if load < 30 else (0, 255, 255) if load < 40 else (0, 0, 255)

            # Метка ТОЛЬКО процент (без кг)
            text = f"{load:.1f}%"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
            
            # Фон для текста
            cv2.rectangle(frame, (x - text_size[0]//2 - 2, y - text_size[1] - 15),
                         (x + text_size[0]//2 + 2, y + 2), (0, 0, 0), -1)
            
            cv2.putText(frame, text, (x - text_size[0]//2, y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
