"""Покадровый анализ видео"""

import logging
from typing import Dict, Any, List
import numpy as np

logger = logging.getLogger(__name__)


class FrameAnalyzer:
    """Анализирует каждый кадр видео"""
    
    def __init__(self):
        self.frame_data = []
    
    def analyze_frame(
        self,
        frame_number: int,
        landmarks: Any,
        timestamp: float
    ) -> Dict[str, Any]:
        """
        Анализирует один кадр
        
        Возвращает:
        - pose_quality: качество позы (0-100)
        - motion_intensity: интенсивность движения (0-40+)
        - angles: углы суставов
        - center_of_mass: центр масс
        - balance_score: оценка баланса
        """
        if not landmarks:
            return {
                'frame_number': frame_number,
                'timestamp': timestamp,
                'pose_quality': 0,
                'motion_intensity': 0,
                'valid': False
            }
        
        # Качество позы на основе visibility landmarks
        pose_quality = self._calculate_pose_quality(landmarks)
        
        # Вычисляем углы суставов
        angles = self._calculate_angles(landmarks)
        
        # Центр масс
        center_of_mass = self._calculate_center_of_mass(landmarks)
        
        # Баланс
        balance_score = self._calculate_balance(landmarks)
        
        frame_info = {
            'frame_number': frame_number,
            'timestamp': timestamp,
            'pose_quality': pose_quality,
            'angles': angles,
            'center_of_mass': center_of_mass,
            'balance_score': balance_score,
            'valid': True
        }
        
        # Сохраняем для истории
        self.frame_data.append(frame_info)
        
        # Интенсивность движения (требует предыдущий кадр)
        if len(self.frame_data) >= 2:
            motion_intensity = self._calculate_motion_intensity(
                self.frame_data[-2],
                frame_info
            )
            frame_info['motion_intensity'] = motion_intensity
        else:
            frame_info['motion_intensity'] = 0
        
        return frame_info
    
    def _calculate_pose_quality(self, landmarks) -> float:
        """
        Вычисляет качество позы на основе visibility ключевых точек
        
        Ключевые точки (MediaPipe):
        - 0: нос, 11-12: плечи, 13-14: локти
        - 15-16: запястья, 23-24: бедра, 25-26: колени
        """
        key_points = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26]
        
        total_visibility = 0
        for idx in key_points:
            if idx < len(landmarks.landmark):
                total_visibility += landmarks.landmark[idx].visibility
        
        # Средняя visibility * 100
        quality = (total_visibility / len(key_points)) * 100
        
        return min(100, max(0, quality))
    
    def _calculate_angles(self, landmarks) -> Dict[str, float]:
        """Вычисляет углы основных суставов"""
        angles = {}
        
        def get_point(idx):
            """Получить координаты точки"""
            lm = landmarks.landmark[idx]
            return np.array([lm.x, lm.y, lm.z])
        
        def calculate_angle(p1, p2, p3):
            """Вычислить угол между тремя точками"""
            v1 = p1 - p2
            v2 = p3 - p2
            
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
            angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
            return np.degrees(angle)
        
        try:
            # Левый локоть (плечо-локоть-запястье)
            angles['left_elbow'] = calculate_angle(
                get_point(11), get_point(13), get_point(15)
            )
            
            # Правый локоть
            angles['right_elbow'] = calculate_angle(
                get_point(12), get_point(14), get_point(16)
            )
            
            # Левое плечо (бедро-плечо-локоть)
            angles['left_shoulder'] = calculate_angle(
                get_point(23), get_point(11), get_point(13)
            )
            
            # Правое плечо
            angles['right_shoulder'] = calculate_angle(
                get_point(24), get_point(12), get_point(14)
            )
            
            # Левое бедро (колено-бедро-плечо)
            angles['left_hip'] = calculate_angle(
                get_point(25), get_point(23), get_point(11)
            )
            
            # Правое бедро
            angles['right_hip'] = calculate_angle(
                get_point(26), get_point(24), get_point(12)
            )
            
            # Левое колено (бедро-колено-лодыжка)
            angles['left_knee'] = calculate_angle(
                get_point(23), get_point(25), get_point(27)
            )
            
            # Правое колено
            angles['right_knee'] = calculate_angle(
                get_point(24), get_point(26), get_point(28)
            )
            
        except Exception as e:
            logger.warning(f"Ошибка вычисления углов: {e}")
        
        return angles
    
    def _calculate_center_of_mass(self, landmarks) -> Dict[str, float]:
        """Вычисляет центр масс"""
        try:
            # Берем ключевые точки тела
            key_points = [11, 12, 23, 24]  # Плечи и бедра
            
            # СМЯГЧАЕМ УСЛОВИЕ: берем точки с видимостью > 0.3 (было 0.5)
            visible_points = [i for i in key_points if landmarks.landmark[i].visibility > 0.3]
            
            if len(visible_points) >= 2:  # Минимум 2 точки
                x_sum = sum(landmarks.landmark[i].x for i in visible_points)
                y_sum = sum(landmarks.landmark[i].y for i in visible_points)
                count = len(visible_points)
                
                return {
                    'x': x_sum / count,
                    'y': y_sum / count
                }
            else:
                # Если видимых точек мало, используем все доступные
                x_sum = sum(landmarks.landmark[i].x for i in key_points)
                y_sum = sum(landmarks.landmark[i].y for i in key_points)
                
                return {
                    'x': x_sum / len(key_points),
                    'y': y_sum / len(key_points)
                }
        except Exception as e:
            logger.warning(f"Используем дефолтный центр масс: {e}")
            return {'x': 0.5, 'y': 0.5}
    
    def _calculate_balance(self, landmarks) -> float:
        """
        Вычисляет оценку баланса (0-100)
        
        На основе:
        - Выравнивание плеч
        - Выравнивание бедер
        - Центр масс между ступнями
        """
        try:
            # Плечи
            left_shoulder = landmarks.landmark[11]
            right_shoulder = landmarks.landmark[12]
            shoulder_diff = abs(left_shoulder.y - right_shoulder.y)
            
            # Бедра
            left_hip = landmarks.landmark[23]
            right_hip = landmarks.landmark[24]
            hip_diff = abs(left_hip.y - right_hip.y)
            
            # Чем меньше разница, тем лучше баланс
            balance = 100 - (shoulder_diff + hip_diff) * 200
            
            return max(0, min(100, balance))
            
        except Exception as e:
            logger.warning(f"Ошибка вычисления баланса: {e}")
            return 50.0
    
    def _calculate_motion_intensity(
        self,
        prev_frame: Dict[str, Any],
        curr_frame: Dict[str, Any]
    ) -> float:
        """
        Вычисляет интенсивность движения между кадрами
        
        На основе смещения центра масс
        """
        # Безопасное получение центра масс
        prev_com = prev_frame.get('center_of_mass', {'x': 0.5, 'y': 0.5})
        curr_com = curr_frame.get('center_of_mass', {'x': 0.5, 'y': 0.5})
        
        # Евклидово расстояние
        distance = np.sqrt(
            (curr_com['x'] - prev_com['x'])**2 +
            (curr_com['y'] - prev_com['y'])**2
        )
        
        # Масштабируем (обычно distance < 0.1)
        intensity = distance * 400  # Обычно дает 0-40
        
        return intensity
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику по всем кадрам"""
        if not self.frame_data:
            return {}
        
        valid_frames = [f for f in self.frame_data if f['valid']]
        
        if not valid_frames:
            return {}
        
        qualities = [f['pose_quality'] for f in valid_frames]
        intensities = [f.get('motion_intensity', 0) for f in valid_frames]
        balance_scores = [f['balance_score'] for f in valid_frames]
        
        return {
            'total_frames': len(self.frame_data),
            'valid_frames': len(valid_frames),
            'avg_pose_quality': np.mean(qualities),
            'min_pose_quality': np.min(qualities),
            'max_pose_quality': np.max(qualities),
            'avg_motion_intensity': np.mean(intensities),
            'avg_balance_score': np.mean(balance_scores),
            'overall_quality': self._calculate_overall_quality(valid_frames)
        }
    
    def _calculate_overall_quality(self, frames: List[Dict[str, Any]]) -> float:
        """
        Вычисляет общее качество сессии
        
        Комбинирует:
        - Среднее качество позы (70%)
        - Стабильность (30%)
        """
        qualities = [f['pose_quality'] for f in frames]
        avg_quality = np.mean(qualities)
        
        # Стабильность (низкое стандартное отклонение = хорошо)
        std_quality = np.std(qualities)
        stability = max(0, 100 - std_quality * 2)
        
        overall = avg_quality * 0.7 + stability * 0.3
        
        return overall
    
    def find_best_worst_frames(self) -> Dict[str, Any]:
        """Находит лучший и худший кадры"""
        valid_frames = [f for f in self.frame_data if f['valid']]
        
        if not valid_frames:
            return {}
        
        best_frame = max(valid_frames, key=lambda f: f['pose_quality'])
        worst_frame = min(valid_frames, key=lambda f: f['pose_quality'])
        
        return {
            'best': {
                'frame_number': best_frame['frame_number'],
                'timestamp': best_frame['timestamp'],
                'quality': best_frame['pose_quality']
            },
            'worst': {
                'frame_number': worst_frame['frame_number'],
                'timestamp': worst_frame['timestamp'],
                'quality': worst_frame['pose_quality']
            }
        }


