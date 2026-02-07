"""
Анализ зажимов и напряжения в теле
Детектирует зоны повышенного напряжения для предсказания травм
"""

import numpy as np
from typing import Dict, List, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class BodyTensionAnalyzer:
    """
    Анализ напряжения и зажимов в теле
    На основе углов суставов и паттернов движения
    """

    # Определение зон напряжения
    TENSION_ZONES = {
        'forearms': {
            'keypoints': [15, 16],  # wrists
            'threshold_high': 25,  # кадров непрерывного хвата
            'threshold_moderate': 15,
        },
        'shoulders': {
            'keypoints': [11, 12, 13, 14],  # shoulders + elbows
            'threshold_high': 35,  # кадров в elevated position
            'threshold_moderate': 20,
        },
        'lumbar': {
            'keypoints': [11, 12, 23, 24],  # shoulders + hips
            'threshold_high': 45,  # градусов наклона таза
            'threshold_moderate': 30,
        },
        'knees': {
            'keypoints': [23, 24, 25, 26, 27, 28],  # hips + knees + ankles
            'threshold_high': (30, 50),  # критический диапазон угла
            'threshold_moderate': (40, 70),
        }
    }

    def __init__(self):
        self.history = []

    def analyze_frame(
        self,
        landmarks,
        frame_number: int
    ) -> Dict[str, Any]:
        """
        Анализирует напряжение в одном кадре

        Returns:
            {
                'forearms': {'left': 'HIGH', 'right': 'MODERATE', ...},
                'shoulders': {...},
                'lumbar': {...},
                'knees': {...}
            }
        """

        if landmarks is None:
            return self._get_empty_tension()

        tension_data = {}

        # Анализ предплечий
        tension_data['forearms'] = self._analyze_forearms(landmarks)

        # Анализ плеч
        tension_data['shoulders'] = self._analyze_shoulders(landmarks)

        # Анализ поясницы
        tension_data['lumbar'] = self._analyze_lumbar(landmarks)

        # Анализ колен
        tension_data['knees'] = self._analyze_knees(landmarks)

        # Сохраняем в историю
        self.history.append({
            'frame': frame_number,
            'tension': tension_data
        })

        return tension_data

    def _analyze_forearms(self, landmarks) -> Dict:
        """Анализ напряжения предплечий"""

        left_wrist = landmarks.landmark[15]
        right_wrist = landmarks.landmark[16]
        left_elbow = landmarks.landmark[13]
        right_elbow = landmarks.landmark[14]

        # Вычисляем углы предплечий
        left_angle = self._calculate_forearm_angle(landmarks, 'left')
        right_angle = self._calculate_forearm_angle(landmarks, 'right')

        # Определяем уровень напряжения по углу
        left_tension = self._classify_forearm_tension(left_angle)
        right_tension = self._classify_forearm_tension(right_angle)

        # Проверяем длительность статичного положения
        if len(self.history) >= 10:
            left_duration = self._calculate_static_duration('left_wrist')
            right_duration = self._calculate_static_duration('right_wrist')

            # Корректируем уровень на основе длительности
            if left_duration > 25:
                left_tension = 'HIGH'
            elif left_duration > 15:
                left_tension = max(left_tension, 'MODERATE')

            if right_duration > 25:
                right_tension = 'HIGH'
            elif right_duration > 15:
                right_tension = max(right_tension, 'MODERATE')
        else:
            left_duration = 0
            right_duration = 0

        return {
            'left': left_tension,
            'right': right_tension,
            'left_angle': left_angle,
            'right_angle': right_angle,
            'left_duration': left_duration,
            'right_duration': right_duration,
            'asymmetry': abs(left_duration - right_duration)
        }

    def _analyze_shoulders(self, landmarks) -> Dict:
        """Анализ напряжения плеч"""

        # Углы плеч
        left_shoulder_angle = self._calculate_angle(
            landmarks, 23, 11, 13  # hip - shoulder - elbow
        )
        right_shoulder_angle = self._calculate_angle(
            landmarks, 24, 12, 14
        )

        # Elevation (поднятие рук над головой)
        left_shoulder_y = landmarks.landmark[11].y
        left_elbow_y = landmarks.landmark[13].y
        left_elevated = left_elbow_y < left_shoulder_y  # локоть выше плеча

        right_shoulder_y = landmarks.landmark[12].y
        right_elbow_y = landmarks.landmark[14].y
        right_elevated = right_elbow_y < right_shoulder_y

        # Считаем длительность elevation
        if len(self.history) >= 10:
            left_elevation_duration = sum(
                1 for h in self.history[-20:]
                if h['tension'].get('shoulders', {}).get('left_elevated', False)
            )
            right_elevation_duration = sum(
                1 for h in self.history[-20:]
                if h['tension'].get('shoulders', {}).get('right_elevated', False)
            )
        else:
            left_elevation_duration = 0
            right_elevation_duration = 0

        # Классификация
        left_tension = 'LOW'
        if left_elevated and left_elevation_duration > 30:
            left_tension = 'HIGH'
        elif left_elevated and left_elevation_duration > 15:
            left_tension = 'MODERATE'
        elif left_shoulder_angle < 60 or left_shoulder_angle > 150:
            left_tension = 'MODERATE'

        right_tension = 'LOW'
        if right_elevated and right_elevation_duration > 30:
            right_tension = 'HIGH'
        elif right_elevated and right_elevation_duration > 15:
            right_tension = 'MODERATE'
        elif right_shoulder_angle < 60 or right_shoulder_angle > 150:
            right_tension = 'MODERATE'

        return {
            'left': left_tension,
            'right': right_tension,
            'left_angle': left_shoulder_angle,
            'right_angle': right_shoulder_angle,
            'left_elevated': left_elevated,
            'right_elevated': right_elevated,
            'left_elevation_duration': left_elevation_duration,
            'right_elevation_duration': right_elevation_duration
        }

    def _analyze_lumbar(self, landmarks) -> Dict:
        """Анализ напряжения поясницы"""

        # Вычисляем наклон таза
        left_hip = landmarks.landmark[23]
        right_hip = landmarks.landmark[24]
        left_shoulder = landmarks.landmark[11]
        right_shoulder = landmarks.landmark[12]

        # Средняя точка бедер и плеч
        hip_center_y = (left_hip.y + right_hip.y) / 2
        shoulder_center_y = (left_shoulder.y + right_shoulder.y) / 2

        # Наклон корпуса (вертикальная разница)
        torso_angle = abs(hip_center_y - shoulder_center_y)

        # Pelvic tilt (асимметрия бедер)
        pelvic_tilt = abs(left_hip.y - right_hip.y) * 100  # нормализуем

        # Spine curvature (разница x координат)
        spine_curve = abs((left_shoulder.x + right_shoulder.x) / 2 -
                         (left_hip.x + right_hip.x) / 2) * 100

        # Классификация
        tension = 'LOW'
        if pelvic_tilt > 45 or spine_curve > 60:
            tension = 'HIGH'
        elif pelvic_tilt > 30 or spine_curve > 45:
            tension = 'MODERATE'

        return {
            'tension': tension,
            'pelvic_tilt': pelvic_tilt,
            'spine_curve': spine_curve,
            'torso_angle': torso_angle
        }

    def _analyze_knees(self, landmarks) -> Dict:
        """Анализ напряжения колен"""

        # Углы колен
        left_knee_angle = self._calculate_angle(
            landmarks, 23, 25, 27  # hip - knee - ankle
        )
        right_knee_angle = self._calculate_angle(
            landmarks, 24, 26, 28
        )

        # Боковая нагрузка (lateral stress) - колени не на одной вертикали с бедрами
        left_hip_x = landmarks.landmark[23].x
        left_knee_x = landmarks.landmark[25].x
        left_lateral = abs(left_hip_x - left_knee_x) * 100

        right_hip_x = landmarks.landmark[24].x
        right_knee_x = landmarks.landmark[26].x
        right_lateral = abs(right_hip_x - right_knee_x) * 100

        # Классификация
        left_tension = 'LOW'
        if 30 <= left_knee_angle <= 50 or left_lateral > 15:
            left_tension = 'HIGH'
        elif 40 <= left_knee_angle <= 70 or left_lateral > 10:
            left_tension = 'MODERATE'

        right_tension = 'LOW'
        if 30 <= right_knee_angle <= 50 or right_lateral > 15:
            right_tension = 'HIGH'
        elif 40 <= right_knee_angle <= 70 or right_lateral > 10:
            right_tension = 'MODERATE'

        return {
            'left': left_tension,
            'right': right_tension,
            'left_angle': left_knee_angle,
            'right_angle': right_knee_angle,
            'left_lateral': left_lateral,
            'right_lateral': right_lateral
        }

    def get_summary(self) -> Dict[str, Any]:
        """
        Возвращает сводку по напряжению за всё видео
        """

        if not self.history:
            return {}

        # Собираем статистику
        forearm_high_count = sum(
            1 for h in self.history
            if h['tension']['forearms']['left'] == 'HIGH' or
               h['tension']['forearms']['right'] == 'HIGH'
        )

        shoulder_high_count = sum(
            1 for h in self.history
            if h['tension']['shoulders']['left'] == 'HIGH' or
               h['tension']['shoulders']['right'] == 'HIGH'
        )

        lumbar_high_count = sum(
            1 for h in self.history
            if h['tension']['lumbar']['tension'] == 'HIGH'
        )

        knee_high_count = sum(
            1 for h in self.history
            if h['tension']['knees']['left'] == 'HIGH' or
               h['tension']['knees']['right'] == 'HIGH'
        )

        total_frames = len(self.history)

        # Процент времени в HIGH tension
        forearm_high_percent = (forearm_high_count / total_frames) * 100
        shoulder_high_percent = (shoulder_high_count / total_frames) * 100
        lumbar_high_percent = (lumbar_high_count / total_frames) * 100
        knee_high_percent = (knee_high_count / total_frames) * 100

        # Общий индекс напряжения
        overall_tension_index = (
            forearm_high_percent * 0.3 +
            shoulder_high_percent * 0.3 +
            lumbar_high_percent * 0.25 +
            knee_high_percent * 0.15
        )

        # Средняя асимметрия предплечий
        asymmetries = [
            h['tension']['forearms'].get('asymmetry', 0)
            for h in self.history
        ]
        avg_asymmetry = np.mean(asymmetries) if asymmetries else 0

        return {
            'overall_tension_index': round(overall_tension_index, 1),
            'zones': {
                'forearms': {
                    'high_percent': round(forearm_high_percent, 1),
                    'avg_asymmetry': round(avg_asymmetry, 1)
                },
                'shoulders': {
                    'high_percent': round(shoulder_high_percent, 1)
                },
                'lumbar': {
                    'high_percent': round(lumbar_high_percent, 1)
                },
                'knees': {
                    'high_percent': round(knee_high_percent, 1)
                }
            },
            'risk_level': self._determine_risk_level(overall_tension_index)
        }

    def _determine_risk_level(self, tension_index: float) -> str:
        """Определяет уровень риска травмы"""
        if tension_index > 60:
            return 'HIGH'
        elif tension_index > 35:
            return 'MODERATE'
        else:
            return 'LOW'

    # Вспомогательные методы

    def _calculate_forearm_angle(self, landmarks, side: str) -> float:
        """Вычисляет угол предплечья"""
        if side == 'left':
            shoulder_idx, elbow_idx, wrist_idx = 11, 13, 15
        else:
            shoulder_idx, elbow_idx, wrist_idx = 12, 14, 16

        return self._calculate_angle(landmarks, shoulder_idx, elbow_idx, wrist_idx)

    def _calculate_angle(self, landmarks, p1_idx: int, p2_idx: int, p3_idx: int) -> float:
        """Вычисляет угол между тремя точками"""
        try:
            p1 = landmarks.landmark[p1_idx]
            p2 = landmarks.landmark[p2_idx]
            p3 = landmarks.landmark[p3_idx]

            if p1.visibility < 0.3 or p2.visibility < 0.3 or p3.visibility < 0.3:
                return 90.0  # default

            v1 = np.array([p1.x - p2.x, p1.y - p2.y])
            v2 = np.array([p3.x - p2.x, p3.y - p2.y])

            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
            angle = np.arccos(np.clip(cos_angle, -1, 1))

            return np.degrees(angle)
        except:
            return 90.0

    def _classify_forearm_tension(self, angle: float) -> str:
        """Классифицирует напряжение предплечья по углу"""
        if angle < 40 or angle > 150:
            return 'HIGH'
        elif angle < 60 or angle > 130:
            return 'MODERATE'
        else:
            return 'LOW'

    def _calculate_static_duration(self, keypoint_name: str) -> int:
        """Вычисляет длительность статичного положения (количество кадров)"""
        if len(self.history) < 10:
            return 0

        # Берем последние 30 кадров
        recent = self.history[-30:]

        # Для упрощения считаем как статичное если мало движения
        # В реальности нужно отслеживать позиции keypoint
        return len(recent)  # Placeholder - нужна более сложная логика

    def _get_empty_tension(self) -> Dict:
        """Возвращает пустые данные о напряжении"""
        return {
            'forearms': {'left': 'UNKNOWN', 'right': 'UNKNOWN'},
            'shoulders': {'left': 'UNKNOWN', 'right': 'UNKNOWN'},
            'lumbar': {'tension': 'UNKNOWN'},
            'knees': {'left': 'UNKNOWN', 'right': 'UNKNOWN'}
        }

    def reset(self):
        """Сброс истории для нового видео"""
        self.history = []


def format_tension_report(tension_summary: Dict) -> str:
    """
    Форматирует отчет о напряжении
    """

    if not tension_summary:
        return "Анализ напряжения недоступен"

    overall = tension_summary['overall_tension_index']
    risk = tension_summary['risk_level']
    zones = tension_summary['zones']

    # Эмодзи для уровней риска
    risk_emoji = {
        'LOW': '🟢',
        'MODERATE': '🟡',
        'HIGH': '🔴'
    }

    report = f"""
⚡ АНАЛИЗ НАПРЯЖЕНИЯ И ЗАЖИМОВ

📊 Общий индекс напряжения: {overall:.1f}/100
{risk_emoji.get(risk, '⚪')} Уровень риска: {risk}

🔍 ДЕТАЛИЗАЦИЯ ПО ЗОНАМ:

💪 Предплечья:
• Время в HIGH напряжении: {zones['forearms']['high_percent']:.1f}%
• Асимметрия нагрузки: {zones['forearms']['avg_asymmetry']:.1f}

🤸 Плечи:
• Время в HIGH напряжении: {zones['shoulders']['high_percent']:.1f}%

🧘 Поясница:
• Время в HIGH напряжении: {zones['lumbar']['high_percent']:.1f}%

🦵 Колени:
• Время в HIGH напряжении: {zones['knees']['high_percent']:.1f}%

💡 РЕКОМЕНДАЦИИ:
"""

    # Добавляем специфические рекомендации
    if zones['forearms']['high_percent'] > 30:
        report += "• ⚠️ Предплечья: высокое напряжение - риск эпикондилита\n"
        report += "  → Эксцентрические упражнения 3×15 ежедневно\n"

    if zones['shoulders']['high_percent'] > 30:
        report += "• ⚠️ Плечи: частое overhead положение\n"
        report += "  → Мобилизация плечевых суставов 2 раза в день\n"

    if zones['lumbar']['high_percent'] > 25:
        report += "• ⚠️ Поясница: проблемы с core stability\n"
        report += "  → Укрепление кора ежедневно\n"

    if zones['forearms']['avg_asymmetry'] > 15:
        report += "• ⚠️ Асимметрия: одна рука перегружена\n"
        report += "  → Работай над равномерным распределением нагрузки\n"

    if risk == 'LOW':
        report += "• ✅ Техника хорошая, зажимов не обнаружено\n"

    return report.strip()
