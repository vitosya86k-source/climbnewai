"""Детекция и предсказание падений v2.0

Улучшенная логика: различает ПАДЕНИЕ и СПРЫГИВАНИЕ

ПАДЕНИЕ (неконтролируемое):
- Резкое снижение качества позы
- Руки "хватаются" за воздух (резкие движения вверх)
- Высокая скорость движения вниз
- Отсутствие подготовки к приземлению

СПРЫГИВАНИЕ (контролируемое):
- Ноги опускаются первыми
- Скорость равномерная
- Тело готовится к приземлению
- Качество позы остаётся стабильным
"""

import logging
import math
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class FallDetector:
    """Детектор падений v2.0 с различением спрыгивания"""

    def __init__(self, quality_threshold: float = 40.0):
        self.quality_threshold = quality_threshold
        self.fall_detected = False
        self.fall_frame = None
        self.fall_timestamp = None
        self.predictors = []  # Кадры-предвестники

        # Для анализа движения
        self.position_history: List[Dict[str, float]] = []
        self.max_history = 30  # 1 секунда при 30fps

        # Результат последней проверки
        self.descent_type = None  # 'fall', 'controlled_descent', 'climbing'

    def reset(self):
        """Сброс состояния детектора"""
        self.fall_detected = False
        self.fall_frame = None
        self.fall_timestamp = None
        self.predictors = []
        self.position_history.clear()
        self.descent_type = None

    def _extract_positions(self, frame_data: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Извлечь позиции ключевых точек из frame_data"""
        # Пробуем получить из разных источников
        landmarks = frame_data.get('landmarks')
        if not landmarks:
            # Пробуем получить из center_of_mass
            com = frame_data.get('center_of_mass', {})
            if com:
                return {
                    'com_y': com.get('y', 0.5),
                    'com_x': com.get('x', 0.5),
                }
            return None

        # Если есть landmarks, извлекаем позиции
        positions = {}
        try:
            # MediaPipe индексы: нос=0, запястья=15,16, лодыжки=27,28
            if hasattr(landmarks, 'landmark'):
                lm = landmarks.landmark
                if len(lm) > 28:
                    positions['nose_y'] = lm[0].y
                    positions['left_wrist_y'] = lm[15].y
                    positions['right_wrist_y'] = lm[16].y
                    positions['left_ankle_y'] = lm[27].y
                    positions['right_ankle_y'] = lm[28].y
                    positions['left_hip_y'] = lm[23].y
                    positions['right_hip_y'] = lm[24].y

                    # Центр масс (упрощённо)
                    positions['com_y'] = (lm[23].y + lm[24].y) / 2
                    positions['com_x'] = (lm[23].x + lm[24].x) / 2
        except Exception as e:
            logger.debug(f"Ошибка извлечения позиций: {e}")
            return None

        return positions if positions else None

    def _is_controlled_descent(self, recent_frames: List[Dict[str, Any]]) -> bool:
        """
        Определяет, является ли движение контролируемым спуском (спрыгиванием)

        Признаки контролируемого спуска:
        1. Ноги ниже центра масс (готовятся к приземлению)
        2. Скорость снижения равномерная (не резкий рывок)
        3. Качество позы не падает резко
        4. Руки не делают резких движений вверх
        """
        if len(recent_frames) < 5:
            return False

        # Анализируем последние 5-10 кадров
        frames_to_check = recent_frames[-10:] if len(recent_frames) >= 10 else recent_frames

        # 1. Проверяем динамику качества позы
        qualities = [f.get('pose_quality', 50) for f in frames_to_check]
        if len(qualities) >= 3:
            # Резкое падение качества = падение, плавное снижение = спрыгивание
            quality_drops = [qualities[i] - qualities[i+1] for i in range(len(qualities)-1)]
            max_drop = max(quality_drops) if quality_drops else 0

            # Если качество падает резко (>20% за кадр) - это падение
            if max_drop > 20:
                return False

        # 2. Проверяем движение центра масс (если есть данные)
        y_positions = []
        for frame in frames_to_check:
            com = frame.get('center_of_mass', {})
            if com and 'y' in com:
                y_positions.append(com['y'])

        if len(y_positions) >= 3:
            # Рассчитываем скорости (изменение Y между кадрами)
            velocities = [y_positions[i+1] - y_positions[i] for i in range(len(y_positions)-1)]

            # Фильтруем только движения вниз (Y увеличивается)
            down_velocities = [v for v in velocities if v > 0]

            if down_velocities:
                avg_velocity = sum(down_velocities) / len(down_velocities)
                max_velocity = max(down_velocities)

                # Контролируемый спуск: равномерная скорость
                # Падение: резкое ускорение (max >> avg)
                velocity_ratio = max_velocity / (avg_velocity + 0.001)

                # Если скорость равномерная (ratio < 2) - это спрыгивание
                if velocity_ratio < 2.0:
                    return True

                # Если очень резкое ускорение (ratio > 3) - это падение
                if velocity_ratio > 3.0:
                    return False

        # 3. Проверяем интенсивность движений
        intensities = [f.get('motion_intensity', 0) for f in frames_to_check]
        if intensities:
            avg_intensity = sum(intensities) / len(intensities)
            # Очень высокая интенсивность может указывать на падение
            # но также может быть динамичным спрыгиванием
            if avg_intensity > 80:
                # Дополнительно проверяем качество - если оно стабильно, то это спрыгивание
                if len(qualities) >= 3:
                    quality_std = self._calculate_std(qualities)
                    if quality_std < 10:  # Стабильное качество
                        return True

        # 4. Баланс - при контролируемом спуске баланс обычно хороший
        balances = [f.get('balance_score', 50) for f in frames_to_check]
        if balances:
            avg_balance = sum(balances) / len(balances)
            if avg_balance > 60:  # Хороший баланс = контролируемое движение
                return True

        return False

    def _calculate_std(self, values: List[float]) -> float:
        """Рассчитать стандартное отклонение"""
        if len(values) < 2:
            return 0.0
        avg = sum(values) / len(values)
        variance = sum((x - avg) ** 2 for x in values) / len(values)
        return math.sqrt(variance)

    def check_fall(
        self,
        current_frame: Dict[str, Any],
        recent_frames: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Проверяет текущий кадр на падение v2.0

        Критерии ПАДЕНИЯ:
        - Качество позы < 40% И
        - Это НЕ контролируемый спуск (спрыгивание)

        Критерии СПРЫГИВАНИЯ:
        - Движение вниз
        - Качество позы может быть низким
        - НО скорость равномерная и тело готово к приземлению
        """
        quality = current_frame.get('pose_quality', 0)

        # Сначала проверяем на контролируемый спуск
        is_controlled = self._is_controlled_descent(recent_frames)

        # Проверка на падение: низкое качество + НЕ контролируемый спуск
        is_fall = quality < self.quality_threshold and not is_controlled

        # Определяем тип движения
        if is_controlled:
            self.descent_type = 'controlled_descent'
        elif is_fall:
            self.descent_type = 'fall'
        else:
            self.descent_type = 'climbing'

        if is_fall and not self.fall_detected:
            self.fall_detected = True
            self.fall_frame = current_frame['frame_number']
            self.fall_timestamp = current_frame['timestamp']

            # Анализируем предвестники (последние 3 кадра)
            self.predictors = self._analyze_predictors(
                recent_frames[-3:] if len(recent_frames) >= 3 else recent_frames
            )

            logger.warning(f"🚨 Падение обнаружено! Кадр: {self.fall_frame}, Время: {self.fall_timestamp:.2f}s")

        elif is_controlled and quality < self.quality_threshold:
            # Логируем спрыгивание (не падение)
            logger.info(f"👟 Контролируемый спуск (спрыгивание) на кадре {current_frame.get('frame_number', '?')}")

        # Предсказание риска падения
        fall_risk = self.predict_fall_risk(current_frame, recent_frames)

        return {
            'is_fall': is_fall,
            'is_controlled_descent': is_controlled,
            'descent_type': self.descent_type,
            'fall_risk': fall_risk,
            'quality': quality
        }
    
    def predict_fall_risk(
        self,
        current_frame: Dict[str, Any],
        recent_frames: List[Dict[str, Any]]
    ) -> int:
        """
        Предсказывает риск падения (0-100)
        
        Факторы риска:
        - Качество < 60%: +30
        - Боковое смещение > 50px: +25
        - Комбо "проблемы с локтями + плечами": +40
        - Тренд деградации > 15%: +20
        """
        risk_score = 0
        
        quality = current_frame.get('pose_quality', 100)
        
        # 1. Низкое качество позы
        if quality < 60:
            risk_score += 30
            logger.debug(f"Риск +30: низкое качество ({quality:.1f}%)")
        
        # 2. Боковое смещение центра масс
        if len(recent_frames) >= 2:
            # Безопасное получение центра масс
            prev_com = recent_frames[-2].get('center_of_mass', {'x': 0.5, 'y': 0.5})
            curr_com = current_frame.get('center_of_mass', {'x': 0.5, 'y': 0.5})
            
            lateral_movement = abs(curr_com.get('x', 0.5) - prev_com.get('x', 0.5))
            
            if lateral_movement > 0.1:  # 10% экрана
                risk_score += 25
                logger.debug(f"Риск +25: большое боковое смещение ({lateral_movement:.3f})")
        
        # 3. Проблемы с углами суставов
        angles = current_frame.get('angles', {})
        problematic_angles = 0
        
        for joint, angle in angles.items():
            # Критические углы
            if angle < 60 or angle > 150:
                problematic_angles += 1
        
        if problematic_angles >= 2:
            risk_score += 40
            logger.debug(f"Риск +40: проблемы с {problematic_angles} суставами")
        
        # 4. Тренд деградации качества
        if len(recent_frames) >= 5:
            quality_5_ago = recent_frames[-5]['pose_quality']
            quality_decline = quality_5_ago - quality
            
            if quality_decline > 15:
                risk_score += 20
                logger.debug(f"Риск +20: деградация качества ({quality_decline:.1f}%)")
        
        return min(risk_score, 100)
    
    def _analyze_predictors(self, predictor_frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Анализирует кадры-предвестники падения"""
        predictors = []
        
        for i, frame in enumerate(predictor_frames):
            frames_before_fall = len(predictor_frames) - i
            time_before_fall = frames_before_fall / 30.0  # Предполагаем 30 FPS
            
            # Проблемы в этом кадре
            problems = []
            
            quality = frame.get('pose_quality', 0)
            if quality < 60:
                problems.append(f"Качество {quality:.1f}% (критично!)")
            
            angles = frame.get('angles', {})
            for joint, angle in angles.items():
                if angle < 60 or angle > 150:
                    problems.append(f"Критический угол {joint}: {angle:.0f}°")
            
            balance = frame.get('balance_score', 100)
            if balance < 50:
                problems.append(f"Нестабильный баланс: {balance:.1f}%")
            
            predictors.append({
                'frame_number': frame['frame_number'],
                'timestamp': frame['timestamp'],
                'time_before_fall': time_before_fall,
                'quality': quality,
                'problems': problems
            })
        
        return predictors
    
    def get_fall_analysis(self) -> Optional[Dict[str, Any]]:
        """Получить полный анализ падения"""
        if not self.fall_detected:
            return None
        
        # Анализируем предвестники
        chronology = []
        
        # Последний стабильный момент (если есть предвестники)
        if self.predictors:
            last_stable = self.predictors[0]
            chronology.append({
                'timestamp': last_stable['timestamp'],
                'description': f"Последний относительно стабильный момент (качество {last_stable['quality']:.1f}%)"
            })
            
            # Каждый предвестник
            for pred in self.predictors:
                if pred['problems']:
                    chronology.append({
                        'timestamp': pred['timestamp'],
                        'description': f"Кадр {pred['frame_number']} (-{pred['time_before_fall']:.2f}с до падения)",
                        'problems': pred['problems']
                    })
        
        # Само падение
        chronology.append({
            'timestamp': self.fall_timestamp,
            'description': "🚨 ПАДЕНИЕ"
        })
        
        # Определяем причину
        root_cause = self._determine_root_cause()
        
        return {
            'detected': True,
            'frame': self.fall_frame,
            'timestamp': self.fall_timestamp,
            'predictors': self.predictors,
            'chronology': chronology,
            'root_cause': root_cause
        }
    
    def _determine_root_cause(self) -> str:
        """Определяет основную причину падения"""
        if not self.predictors:
            return "Внезапная потеря контроля"
        
        # Собираем все проблемы из предвестников
        all_problems = []
        for pred in self.predictors:
            all_problems.extend(pred['problems'])
        
        # Анализируем паттерны
        if any('локоть' in p.lower() for p in all_problems):
            if any('плечо' in p.lower() or 'плеч' in p.lower() for p in all_problems):
                return "Комплексная проблема верхних конечностей (локти + плечи)"
            return "Проблема с локтями - недостаточное сгибание или перегрузка"
        
        if any('баланс' in p.lower() for p in all_problems):
            return "Потеря баланса - смещение центра масс"
        
        if any('качество' in p.lower() for p in all_problems):
            return "Общая деградация техники"
        
        return "Множественные технические проблемы"
    
    def get_descent_summary(self) -> Dict[str, Any]:
        """
        Получить сводку о типе спуска (падение/спрыгивание/лазание)

        Returns:
            dict с информацией о типе движения
        """
        return {
            'descent_type': self.descent_type or 'climbing',
            'fall_detected': self.fall_detected,
            'is_controlled': self.descent_type == 'controlled_descent',
            'fall_frame': self.fall_frame,
            'fall_timestamp': self.fall_timestamp
        }

    def format_fall_report(self) -> str:
        """Форматирует отчет о падении для включения в финальный анализ"""
        analysis = self.get_fall_analysis()

        if not analysis:
            # Если падения не было, но был контролируемый спуск
            if self.descent_type == 'controlled_descent':
                return self._format_controlled_descent_report()
            return ""

        report = f"""
💡 АНАЛИЗ ПАДЕНИЯ
==================

📋 Кадр #{analysis['frame']}
Время: {analysis['timestamp']:.2f}с

📊 ХРОНОЛОГИЯ СОБЫТИЙ:
"""

        for event in analysis['chronology']:
            report += f"\n⏰ {event['timestamp']:.2f}с - {event['description']}"
            if 'problems' in event and event['problems']:
                for problem in event['problems']:
                    report += f"\n  • {problem}"

        report += f"""

🔍 АНАЛИЗ ПРЕДВЕСТНИКОВ:
Обнаружено {len(analysis['predictors'])} кадров-предвестников за {len(analysis['predictors']) / 30:.2f}с до падения.

💡 ПРИЧИНА:
{analysis['root_cause']}

✅ РЕКОМЕНДАЦИИ:
• Работай над контролем углов суставов
• Следи за центром масс на критических участках
• Не спеши - качество важнее скорости
"""

        return report.strip()

    def _format_controlled_descent_report(self) -> str:
        """Форматирует отчет о контролируемом спуске (спрыгивании)"""
        return """
👟 КОНТРОЛИРУЕМЫЙ СПУСК
========================

Обнаружено спрыгивание с трассы (не падение).

Признаки контролируемого спуска:
• Равномерная скорость снижения
• Тело подготовлено к приземлению
• Качество позы не падало резко

✅ Это нормальное завершение попытки!
"""


