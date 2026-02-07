"""
Дополнительные метрики для анализа скалолазания

Метрики:
1. Стабильность (Stability)
2. Истощение (Exhaustion)
3. Эффективность рук (Arm Efficiency)
4. Эффективность ног (Leg Efficiency)
5. Восстановление (Recovery)
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Any, Optional
from collections import deque
import logging

logger = logging.getLogger(__name__)


class AdditionalMetricsAnalyzer:
    """Анализатор дополнительных метрик"""
    
    def __init__(self, history_size: int = 90):
        """
        Args:
            history_size: размер истории для анализа
        """
        self.history_size = history_size
        
        # История центра масс
        self.center_of_mass_history: List[Tuple[float, float]] = []
        
        # История метрик для анализа истощения
        self.metrics_timeline: List[Dict[str, float]] = []
        
        # История распределения нагрузки
        self.weight_distribution_history: List[Dict[str, float]] = []
        
        # Позиции отдыха
        self.rest_positions: List[Dict[str, Any]] = []
        
        self.frame_number = 0
        
    def reset(self):
        """Сброс всех историй"""
        self.center_of_mass_history = []
        self.metrics_timeline = []
        self.weight_distribution_history = []
        self.rest_positions = []
        self.frame_number = 0
    
    def analyze_frame(
        self,
        landmarks,
        frame_number: int,
        frame_data: Optional[Dict[str, Any]] = None,
        technique_metrics: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Анализ кадра и вычисление дополнительных метрик
        
        Args:
            landmarks: MediaPipe landmarks
            frame_number: номер кадра
            frame_data: данные кадра
            technique_metrics: метрики техники для анализа истощения
            
        Returns:
            dict с метриками
        """
        self.frame_number = frame_number
        
        if not landmarks:
            return self._get_default_metrics()
        
        # Обновляем историю центра масс
        com = self._calculate_center_of_mass(landmarks)
        if com:
            self.center_of_mass_history.append(com)
            if len(self.center_of_mass_history) > self.history_size:
                self.center_of_mass_history.pop(0)
        
        # Обновляем историю метрик для анализа истощения
        if technique_metrics:
            self.metrics_timeline.append(technique_metrics.copy())
            if len(self.metrics_timeline) > self.history_size * 10:  # Больше истории для истощения
                self.metrics_timeline.pop(0)
        
        # Обновляем распределение нагрузки
        weight_dist = self._calculate_weight_distribution(landmarks)
        if weight_dist:
            self.weight_distribution_history.append(weight_dist)
            if len(self.weight_distribution_history) > self.history_size:
                self.weight_distribution_history.pop(0)
        
        # Анализируем позиции отдыха
        self._analyze_rest_positions(landmarks, frame_data)
        
        # Вычисляем метрики
        metrics = {
            'stability': self._calculate_stability(),
            'exhaustion': self._calculate_exhaustion(),
            'arm_efficiency': self._calculate_arm_efficiency(),
            'leg_efficiency': self._calculate_leg_efficiency(),
            'recovery': self._calculate_recovery(),
            'productivity': self._calculate_productivity(landmarks, frame_data),
            'economy': self._calculate_economy(),
            'balance': self._calculate_balance(landmarks),
        }
        
        return metrics
    
    def _calculate_center_of_mass(self, landmarks) -> Optional[Tuple[float, float]]:
        """Вычисление центра масс"""
        try:
            # Используем ключевые точки для расчета центра масс
            key_points = []
            weights = []
            
            # Плечи (вес 0.2)
            if len(landmarks.landmark) > 11:
                left_shoulder = landmarks.landmark[11]
                if left_shoulder.visibility > 0.5:
                    key_points.append((left_shoulder.x, left_shoulder.y))
                    weights.append(0.1)
            
            if len(landmarks.landmark) > 12:
                right_shoulder = landmarks.landmark[12]
                if right_shoulder.visibility > 0.5:
                    key_points.append((right_shoulder.x, right_shoulder.y))
                    weights.append(0.1)
            
            # Бёдра (вес 0.4 - центр масс тела)
            if len(landmarks.landmark) > 23:
                left_hip = landmarks.landmark[23]
                if left_hip.visibility > 0.5:
                    key_points.append((left_hip.x, left_hip.y))
                    weights.append(0.2)
            
            if len(landmarks.landmark) > 24:
                right_hip = landmarks.landmark[24]
                if right_hip.visibility > 0.5:
                    key_points.append((right_hip.x, right_hip.y))
                    weights.append(0.2)
            
            # Колени (вес 0.2)
            if len(landmarks.landmark) > 25:
                left_knee = landmarks.landmark[25]
                if left_knee.visibility > 0.5:
                    key_points.append((left_knee.x, left_knee.y))
                    weights.append(0.1)
            
            if len(landmarks.landmark) > 26:
                right_knee = landmarks.landmark[26]
                if right_knee.visibility > 0.5:
                    key_points.append((right_knee.x, right_knee.y))
                    weights.append(0.1)
            
            # Лодыжки (вес 0.2)
            if len(landmarks.landmark) > 27:
                left_ankle = landmarks.landmark[27]
                if left_ankle.visibility > 0.5:
                    key_points.append((left_ankle.x, left_ankle.y))
                    weights.append(0.1)
            
            if len(landmarks.landmark) > 28:
                right_ankle = landmarks.landmark[28]
                if right_ankle.visibility > 0.5:
                    key_points.append((right_ankle.x, right_ankle.y))
                    weights.append(0.1)
            
            if len(key_points) == 0:
                return None
            
            # Нормализуем веса
            total_weight = sum(weights)
            if total_weight == 0:
                return None
            
            weights = [w / total_weight for w in weights]
            
            # Взвешенный центр масс
            com_x = sum(point[0] * weight for point, weight in zip(key_points, weights))
            com_y = sum(point[1] * weight for point, weight in zip(key_points, weights))
            
            return (com_x, com_y)
        except Exception as e:
            logger.warning(f"Ошибка расчета центра масс: {e}")
            return None
    
    def _calculate_stability(self) -> float:
        """
        Стабильность (Stability)
        Дисперсия положения центра масс за скользящее окно
        """
        if len(self.center_of_mass_history) < 30:
            return 50.0  # Недостаточно данных
        
        window = 30
        variances = []
        
        for i in range(len(self.center_of_mass_history) - window):
            segment = self.center_of_mass_history[i:i+window]
            
            # Вычисляем дисперсию по X и Y
            x_coords = [point[0] for point in segment]
            y_coords = [point[1] for point in segment]
            
            var_x = np.var(x_coords)
            var_y = np.var(y_coords)
            
            # Общая дисперсия
            total_variance = var_x + var_y
            variances.append(total_variance)
        
        if len(variances) == 0:
            return 50.0
        
        avg_variance = np.mean(variances)
        
        # Преобразуем в балл (низкая дисперсия = высокий балл)
        # Масштабируем: variance обычно в диапазоне 0-0.01 для нормализованных координат
        score = max(0, 100 - avg_variance * 10000)
        
        # Шкала оценки
        if score >= 80:
            return score  # 80-100%: Отличный контроль
        elif score >= 60:
            return score  # 60-80%: Хорошая стабильность
        elif score >= 40:
            return score  # 40-60%: Заметное дрожание
        else:
            return max(0, score)  # < 40%: Сильная нестабильность
    
    def _calculate_exhaustion(self) -> float:
        """
        Истощение (Exhaustion)
        Сравнение качества движений в начале и конце маршрута
        """
        if len(self.metrics_timeline) < 20:
            return 0.0  # Недостаточно данных
        
        # Делим маршрут на 4 части
        total_frames = len(self.metrics_timeline)
        quarter_size = total_frames // 4
        
        if quarter_size < 5:
            return 0.0
        
        quarters = [
            self.metrics_timeline[0:quarter_size],
            self.metrics_timeline[quarter_size:quarter_size*2],
            self.metrics_timeline[quarter_size*2:quarter_size*3],
            self.metrics_timeline[quarter_size*3:]
        ]
        
        # Средние показатели по четвертям (используем среднее всех метрик техники)
        def mean_quality(quarter_data):
            if len(quarter_data) == 0:
                return 50.0
            
            all_scores = []
            for frame_metrics in quarter_data:
                if isinstance(frame_metrics, dict):
                    scores = [v for v in frame_metrics.values() if isinstance(v, (int, float))]
                    if scores:
                        all_scores.extend(scores)
            
            if len(all_scores) == 0:
                return 50.0
            
            return np.mean(all_scores)
        
        q1_quality = mean_quality(quarters[0])  # первая четверть
        q4_quality = mean_quality(quarters[3])  # последняя четверть
        
        if q1_quality == 0:
            return 0.0
        
        # Падение качества
        degradation = ((q1_quality - q4_quality) / q1_quality) * 100
        
        # Истощение = насколько упало качество
        return min(100, max(0, degradation))
    
    def _calculate_weight_distribution(self, landmarks) -> Optional[Dict[str, float]]:
        """Расчет распределения нагрузки на конечности"""
        try:
            if len(landmarks.landmark) < 28:
                return None
            
            # Получаем позиции ключевых точек
            left_wrist = landmarks.landmark[15] if len(landmarks.landmark) > 15 else None
            right_wrist = landmarks.landmark[16] if len(landmarks.landmark) > 16 else None
            left_ankle = landmarks.landmark[27] if len(landmarks.landmark) > 27 else None
            right_ankle = landmarks.landmark[28] if len(landmarks.landmark) > 28 else None
            left_hip = landmarks.landmark[23] if len(landmarks.landmark) > 23 else None
            right_hip = landmarks.landmark[24] if len(landmarks.landmark) > 24 else None
            
            if not all([left_wrist, right_wrist, left_ankle, right_ankle, left_hip, right_hip]):
                return None
            
            if any([lm.visibility < 0.5 for lm in [left_wrist, right_wrist, left_ankle, right_ankle, left_hip, right_hip]]):
                return None
            
            # Центр масс (бёдра)
            hip_center_y = (left_hip.y + right_hip.y) / 2
            
            # Высота конечностей относительно центра масс
            left_arm_height = abs(hip_center_y - left_wrist.y)
            right_arm_height = abs(hip_center_y - right_wrist.y)
            left_leg_support = abs(left_ankle.y - hip_center_y)
            right_leg_support = abs(right_ankle.y - hip_center_y)
            
            # Нормализация
            total = left_arm_height + right_arm_height + left_leg_support + right_leg_support
            
            if total == 0:
                return None
            
            # Распределение (чем выше конечность относительно ЦМ, тем больше нагрузка)
            left_arm = (left_arm_height / total) * 100 * 1.5
            right_arm = (right_arm_height / total) * 100 * 1.5
            left_leg = (left_leg_support / total) * 100 * 1.2
            right_leg = (right_leg_support / total) * 100 * 1.2
            
            # Нормализация до 100%
            total_load = left_arm + right_arm + left_leg + right_leg
            if total_load > 0:
                left_arm = (left_arm / total_load) * 100
                right_arm = (right_arm / total_load) * 100
                left_leg = (left_leg / total_load) * 100
                right_leg = (right_leg / total_load) * 100
            
            return {
                'left_arm': left_arm,
                'right_arm': right_arm,
                'left_leg': left_leg,
                'right_leg': right_leg
            }
        except Exception as e:
            logger.warning(f"Ошибка расчета распределения нагрузки: {e}")
            return None
    
    def _calculate_arm_efficiency(self) -> float:
        """
        Эффективность рук (Arm Efficiency)
        Процент веса, который несут руки (норма: 30-40%)
        """
        if len(self.weight_distribution_history) == 0:
            return 50.0
        
        # Среднее распределение за историю
        avg_left_arm = np.mean([w['left_arm'] for w in self.weight_distribution_history])
        avg_right_arm = np.mean([w['right_arm'] for w in self.weight_distribution_history])
        
        arm_percentage = avg_left_arm + avg_right_arm
        
        # Оценка
        if arm_percentage <= 40:
            score = 100
        elif arm_percentage <= 50:
            score = 100 - (arm_percentage - 40) * 5
        else:
            score = max(0, 50 - (arm_percentage - 50) * 3)
        
        return max(0.0, min(100.0, score))
    
    def _calculate_leg_efficiency(self) -> float:
        """
        Эффективность ног (Leg Efficiency)
        Процент веса, который несут ноги (норма: 60-70%)
        """
        if len(self.weight_distribution_history) == 0:
            return 50.0
        
        # Среднее распределение за историю
        avg_left_leg = np.mean([w['left_leg'] for w in self.weight_distribution_history])
        avg_right_leg = np.mean([w['right_leg'] for w in self.weight_distribution_history])
        
        leg_percentage = avg_left_leg + avg_right_leg
        
        # Оценка (идеал: 60-70%)
        score = min(100, leg_percentage * 1.5)
        
        return max(0.0, min(100.0, score))
    
    def _analyze_rest_positions(self, landmarks, frame_data: Optional[Dict[str, Any]]):
        """Анализ позиций отдыха"""
        if not landmarks or not frame_data:
            return
        
        # Определяем позицию отдыха по нескольким критериям:
        # 1. Низкая скорость движения (из frame_data)
        # 2. Выпрямленные руки (угол локтя > 150°)
        # 3. Стабильное положение
        
        motion_intensity = frame_data.get('motion_intensity', 50)
        
        # Проверяем углы локтей
        left_elbow_angle = self._calculate_elbow_angle(landmarks, 'left')
        right_elbow_angle = self._calculate_elbow_angle(landmarks, 'right')
        
        # Позиция отдыха: низкая активность + выпрямленные руки
        is_rest = (
            motion_intensity < 20 and
            (left_elbow_angle is None or left_elbow_angle > 150) and
            (right_elbow_angle is None or right_elbow_angle > 150)
        )
        
        if is_rest:
            # Проверяем, не является ли это продолжением предыдущей паузы
            if len(self.rest_positions) > 0:
                last_rest = self.rest_positions[-1]
                if self.frame_number - last_rest['end_frame'] < 10:  # Продолжение паузы
                    last_rest['end_frame'] = self.frame_number
                    last_rest['duration'] = (last_rest['end_frame'] - last_rest['start_frame']) * 0.033  # Предполагаем 30 FPS
                    return
            
            # Новая пауза
            self.rest_positions.append({
                'start_frame': self.frame_number,
                'end_frame': self.frame_number,
                'duration': 0.033,  # 1 кадр
                'arm_angle': min(
                    left_elbow_angle if left_elbow_angle else 180,
                    right_elbow_angle if right_elbow_angle else 180
                ),
                'tension_before': frame_data.get('motion_intensity', 50),
                'tension_during': motion_intensity
            })
            
            # Ограничиваем размер истории
            if len(self.rest_positions) > 20:
                self.rest_positions.pop(0)
    
    def _calculate_elbow_angle(self, landmarks, side: str) -> Optional[float]:
        """Вычисление угла локтя"""
        try:
            if side == 'left':
                shoulder_idx = 11
                elbow_idx = 13
                wrist_idx = 15
            else:
                shoulder_idx = 12
                elbow_idx = 14
                wrist_idx = 16
            
            if len(landmarks.landmark) <= max(shoulder_idx, elbow_idx, wrist_idx):
                return None
            
            shoulder = landmarks.landmark[shoulder_idx]
            elbow = landmarks.landmark[elbow_idx]
            wrist = landmarks.landmark[wrist_idx]
            
            if any([lm.visibility < 0.5 for lm in [shoulder, elbow, wrist]]):
                return None
            
            # Векторы
            vec1 = (shoulder.x - elbow.x, shoulder.y - elbow.y)
            vec2 = (wrist.x - elbow.x, wrist.y - elbow.y)
            
            # Угол между векторами
            dot = vec1[0] * vec2[0] + vec1[1] * vec2[1]
            len1 = math.sqrt(vec1[0]**2 + vec1[1]**2)
            len2 = math.sqrt(vec2[0]**2 + vec2[1]**2)
            
            if len1 == 0 or len2 == 0:
                return None
            
            cos_angle = dot / (len1 * len2)
            cos_angle = max(-1, min(1, cos_angle))
            angle = math.degrees(math.acos(cos_angle))
            
            return angle
        except Exception:
            return None
    
    def _calculate_recovery(self) -> float:
        """
        Восстановление (Recovery)
        Умение находить позиции для отдыха и эффективно восстанавливаться
        """
        if len(self.rest_positions) == 0:
            return 50.0  # Нет пауз — неизвестно
        
        recovery_scores = []
        
        for rest in self.rest_positions:
            # Насколько расслаблены мышцы в паузе
            tension_drop = rest.get('tension_before', 50) - rest.get('tension_during', 30)
            
            # Длительность отдыха (2-5 сек = оптимально)
            duration = rest.get('duration', 0)
            if 2 <= duration <= 5:
                duration_score = 100
            else:
                duration_score = 70
            
            # Выпрямлены ли руки (снятие нагрузки)
            arm_angle = rest.get('arm_angle', 150)
            if arm_angle > 150:
                arm_angle_score = 100
            else:
                arm_angle_score = 50
            
            # Общая оценка восстановления
            recovery_score = (tension_drop * 2 + duration_score + arm_angle_score) / 4
            recovery_scores.append(recovery_score)
        
        avg_score = np.mean(recovery_scores) if recovery_scores else 50.0
        
        return max(0.0, min(100.0, avg_score))
    
    def _calculate_productivity(self, landmarks, frame_data: Optional[Dict[str, Any]]) -> float:
        """
        Продуктивность (Productivity) - по формуле из METRICS_FORMULAS_ADDON.md
        Эффект/затраты: полезное движение / общее движение
        """
        if len(self.center_of_mass_history) < 10:
            return 50.0
        
        # Полезное движение = вертикальное перемещение вверх
        useful_movement = 0.0
        for i in range(1, len(self.center_of_mass_history)):
            prev_y = self.center_of_mass_history[i - 1][1]
            curr_y = self.center_of_mass_history[i][1]
            vertical_delta = prev_y - curr_y  # Меньше Y = выше
            if vertical_delta > 0:  # только вверх
                useful_movement += vertical_delta
        
        # Общее движение = все перемещения
        total_movement = 0.0
        for i in range(1, len(self.center_of_mass_history)):
            prev = self.center_of_mass_history[i - 1]
            curr = self.center_of_mass_history[i]
            dist = math.sqrt((curr[0] - prev[0])**2 + (curr[1] - prev[1])**2)
            total_movement += dist
        
        if total_movement < 0.001:
            return 50.0
        
        # Средний уровень напряжения (из frame_data или дефолт)
        avg_tension = 50.0
        if frame_data:
            avg_tension = frame_data.get('motion_intensity', 50)
        
        # Продуктивность = (полезное / общее) × (100 - напряжение) / 50
        base_productivity = (useful_movement / total_movement) * 100
        tension_factor = (100 - avg_tension) / 50  # от 0 до 2
        
        score = base_productivity * tension_factor
        
        return max(10.0, min(100.0, score))
    
    def _calculate_economy(self) -> float:
        """
        Экономичность (Economy) - упрощенная версия по формуле из METRICS_FORMULAS_ADDON.md
        Комбинация quiet_feet, grip_release и stability
        """
        # Используем упрощенную формулу: комбинация других метрик
        # Для этого нужны technique_metrics, но их нет в этом контексте
        # Используем альтернативу: соотношение прямого пути к фактическому
        
        if len(self.center_of_mass_history) < 10:
            return 50.0
        
        # Прямое расстояние от старта до текущей позиции
        start = self.center_of_mass_history[0]
        end = self.center_of_mass_history[-1]
        direct_distance = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
        
        # Общий пройденный путь
        total_path = 0.0
        for i in range(1, len(self.center_of_mass_history)):
            prev = self.center_of_mass_history[i - 1]
            curr = self.center_of_mass_history[i]
            total_path += math.sqrt((curr[0] - prev[0])**2 + (curr[1] - prev[1])**2)
        
        if total_path < 0.001:
            return 50.0
        
        # Коэффициент лишних движений
        movement_ratio = total_path / direct_distance if direct_distance > 0.001 else 1.0
        
        # Шкала оценки по формуле из файла
        if movement_ratio <= 1.0:
            score = 100
        elif movement_ratio <= 1.5:
            score = 100 - (movement_ratio - 1.0) * 60  # 100 → 70
        elif movement_ratio <= 2.0:
            score = 70 - (movement_ratio - 1.5) * 40   # 70 → 50
        else:
            score = max(10, 50 - (movement_ratio - 2.0) * 20)
        
        return max(10.0, min(100.0, score))
    
    def _calculate_balance(self, landmarks) -> float:
        """
        Баланс (Balance) - упрощенная версия по формуле из METRICS_FORMULAS_ADDON.md
        Комбинация stability * 0.4 + hip_position * 0.3 + diagonal * 0.3
        """
        if not landmarks or len(self.center_of_mass_history) < 5:
            return 50.0
        
        # Стабильность
        stability_score = self._calculate_stability()
        
        # Оцениваем положение таза (hip_position) - упрощенно
        hip_score = 50.0
        try:
            if len(landmarks.landmark) > 23:
                left_hip = landmarks.landmark[23]
                right_hip = landmarks.landmark[24] if len(landmarks.landmark) > 24 else None
                if right_hip and left_hip.visibility > 0.5 and right_hip.visibility > 0.5:
                    # Упрощенная оценка: близко ли таз к стене (по Y координате)
                    hip_y = (left_hip.y + right_hip.y) / 2
                    # Чем выше таз (меньше Y), тем лучше
                    hip_score = max(0, min(100, (1.0 - hip_y) * 100))
        except:
            pass
        
        # Diagonal score - упрощенно, используем стабильность как прокси
        diagonal_score = stability_score * 0.8
        
        # Комбинация по формуле: stability * 0.4 + hip_position * 0.3 + diagonal * 0.3
        score = (stability_score * 0.4 + hip_score * 0.3 + diagonal_score * 0.3)
        
        return max(10.0, min(100.0, score))
    
    def _get_default_metrics(self) -> Dict[str, float]:
        """Возвращает метрики по умолчанию"""
        return {
            'stability': 50.0,
            'exhaustion': 0.0,
            'arm_efficiency': 50.0,
            'leg_efficiency': 50.0,
            'recovery': 50.0,
            'productivity': 50.0,
            'economy': 50.0,
            'balance': 50.0,
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Возвращает сводку по всем метрикам"""
        return {
            'metrics': self._get_default_metrics(),
            'center_of_mass_count': len(self.center_of_mass_history),
            'metrics_timeline_count': len(self.metrics_timeline),
            'rest_positions_count': len(self.rest_positions)
        }
