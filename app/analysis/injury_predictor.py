"""
Предсказание травм на основе анализа напряжения и паттернов движения
Адаптировано из advanced_predictive_analytics.py
"""

import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    LOW = "низкий"
    MODERATE = "умеренный"
    HIGH = "высокий"
    CRITICAL = "критический"


class TraumaType(Enum):
    ACUTE = "острая"
    OVERUSE = "перегрузочная"
    CHRONIC = "хроническая"


@dataclass
class InjuryPrediction:
    """Прогноз конкретной травмы"""
    injury_type: str
    body_part: str
    risk_level: RiskLevel
    trauma_type: TraumaType
    probability: float  # 0-100%
    timeline: str
    contributing_factors: List[str]
    prevention_measures: List[str]
    early_indicators: List[str]
    self_test: str


class InjuryPredictor:
    """
    Предсказывает риски травм на основе:
    - Анализа напряжения (tension_analyzer)
    - BoulderVision метрик
    - Паттернов движения
    """

    # Модели травм с пороговыми значениями
    INJURY_MODELS = {
        'medial_epicondylitis': {
            'name': 'Медиальный эпикондилит (локоть гольфиста)',
            'body_parts': ['предплечья', 'локти'],
            'risk_factors': {
                'forearm_tension_high_frequency': 0.3,  # 30% кадров с HIGH
                'forearm_grip_duration': 0.25,
                'elbow_angle_critical': 0.2,
                'asymmetric_usage': 0.15
            },
            'accumulation_threshold': 0.60,
            'acute_threshold': 0.85,
            'timeline_moderate': '3-6 недель',
            'timeline_high': '1-3 недели',
            'timeline_critical': '3-7 дней'
        },

        'shoulder_impingement': {
            'name': 'Импинджмент-синдром плеча',
            'body_parts': ['плечи'],
            'risk_factors': {
                'shoulder_elevation_high': 0.25,
                'overhead_duration': 0.2,
                'shoulder_angle_critical': 0.2,
                'poor_posture': 0.15
            },
            'accumulation_threshold': 0.60,
            'acute_threshold': 0.80,
            'timeline_moderate': '4-8 недель',
            'timeline_high': '2-4 недели',
            'timeline_critical': '1-2 недели'
        },

        'lumbar_strain': {
            'name': 'Растяжение поясничных мышц',
            'body_parts': ['поясница', 'кор'],
            'risk_factors': {
                'core_weakness': 0.3,
                'pelvic_tilt_excessive': 0.25,
                'spine_instability': 0.25,
                'fatigue_form_breakdown': 0.2
            },
            'accumulation_threshold': 0.55,
            'acute_threshold': 0.75,
            'timeline_moderate': '2-4 недели',
            'timeline_high': '1-2 недели',
            'timeline_critical': '2-5 дней'
        },

        'knee_ligament_stress': {
            'name': 'Стресс связок колена',
            'body_parts': ['колени'],
            'risk_factors': {
                'knee_angle_critical': 0.3,
                'lateral_stress': 0.25,
                'dynamic_load': 0.25,
                'landing_impact': 0.2
            },
            'accumulation_threshold': 0.60,
            'acute_threshold': 0.80,
            'timeline_moderate': '3-6 недель',
            'timeline_high': '2-3 недели',
            'timeline_critical': '1 неделя'
        }
    }

    def predict_injuries(
        self,
        tension_summary: Dict,
        video_analysis: Dict,
        duration_seconds: float
    ) -> Dict[str, InjuryPrediction]:
        """
        Предсказывает риски травм

        Args:
            tension_summary: Сводка от BodyTensionAnalyzer
            video_analysis: Полный результат анализа видео
            duration_seconds: Длительность видео

        Returns:
            Dict с прогнозами травм (key = injury_type)
        """

        predictions = {}

        # Анализируем каждый тип травмы
        for injury_type, model in self.INJURY_MODELS.items():
            risk_score = self._calculate_injury_risk(
                injury_type,
                model,
                tension_summary,
                video_analysis,
                duration_seconds
            )

            if risk_score > 0.25:  # Минимальный порог для отчета
                prediction = self._create_prediction(
                    injury_type,
                    model,
                    risk_score,
                    tension_summary,
                    video_analysis
                )
                predictions[injury_type] = prediction

        return predictions

    def _calculate_injury_risk(
        self,
        injury_type: str,
        model: Dict,
        tension_summary: Dict,
        video_analysis: Dict,
        duration: float
    ) -> float:
        """Вычисляет риск конкретной травмы"""

        risk_score = 0.0
        zones = tension_summary.get('zones', {})
        bv = video_analysis.get('bouldervision', {})

        # Медиальный эпикондилит
        if injury_type == 'medial_epicondylitis':
            # Напряжение предплечий
            forearm_high = zones.get('forearms', {}).get('high_percent', 0)
            if forearm_high > 30:
                risk_score += model['risk_factors']['forearm_tension_high_frequency']

            # Асимметрия
            asymmetry = zones.get('forearms', {}).get('avg_asymmetry', 0)
            if asymmetry > 15:
                risk_score += model['risk_factors']['asymmetric_usage']

            # Длительность (долгое видео = больше риск)
            if duration > 60:
                risk_score += model['risk_factors']['forearm_grip_duration'] * 0.5

        # Импинджмент плеча
        elif injury_type == 'shoulder_impingement':
            shoulder_high = zones.get('shoulders', {}).get('high_percent', 0)
            if shoulder_high > 30:
                risk_score += model['risk_factors']['shoulder_elevation_high']

            # Overhead duration
            if shoulder_high > 40:
                risk_score += model['risk_factors']['overhead_duration']

        # Поясничное растяжение
        elif injury_type == 'lumbar_strain':
            lumbar_high = zones.get('lumbar', {}).get('high_percent', 0)
            if lumbar_high > 25:
                risk_score += model['risk_factors']['core_weakness']

            # Усталость приводит к деградации формы
            fatigue_data = video_analysis.get('fatigue_analysis', {})
            fatigue_rate = fatigue_data.get('fatigue_rate', 0)
            if abs(fatigue_rate) > 0.3:
                risk_score += model['risk_factors']['fatigue_form_breakdown']

        # Стресс колена
        elif injury_type == 'knee_ligament_stress':
            knee_high = zones.get('knees', {}).get('high_percent', 0)
            if knee_high > 20:
                risk_score += model['risk_factors']['knee_angle_critical']

            # Динамическая нагрузка
            avg_vr = bv.get('avg_velocity_ratio', 1.0)
            if avg_vr > 1.8:  # Высокая динамика
                risk_score += model['risk_factors']['dynamic_load']

        return min(1.0, risk_score)

    def _create_prediction(
        self,
        injury_type: str,
        model: Dict,
        risk_score: float,
        tension_summary: Dict,
        video_analysis: Dict
    ) -> InjuryPrediction:
        """Создает объект прогноза травмы"""

        # Определяем уровень риска и временные рамки
        if risk_score >= model['acute_threshold']:
            risk_level = RiskLevel.CRITICAL
            timeline = model['timeline_critical']
            trauma_type = TraumaType.ACUTE
        elif risk_score >= model['accumulation_threshold']:
            risk_level = RiskLevel.HIGH
            timeline = model['timeline_high']
            trauma_type = TraumaType.OVERUSE
        elif risk_score >= 0.40:
            risk_level = RiskLevel.MODERATE
            timeline = model['timeline_moderate']
            trauma_type = TraumaType.OVERUSE
        else:
            risk_level = RiskLevel.LOW
            timeline = "более 2 месяцев"
            trauma_type = TraumaType.CHRONIC

        # Генерируем специфичные данные
        contributing_factors = self._identify_factors(
            injury_type, tension_summary, video_analysis
        )

        prevention_measures = self._get_prevention_measures(injury_type, risk_level)
        early_indicators = self._get_early_indicators(injury_type)
        self_test = self._get_self_test(injury_type)

        return InjuryPrediction(
            injury_type=model['name'],
            body_part=", ".join(model['body_parts']),
            risk_level=risk_level,
            trauma_type=trauma_type,
            probability=risk_score * 100,
            timeline=timeline,
            contributing_factors=contributing_factors,
            prevention_measures=prevention_measures,
            early_indicators=early_indicators,
            self_test=self_test
        )

    def _identify_factors(
        self,
        injury_type: str,
        tension_summary: Dict,
        video_analysis: Dict
    ) -> List[str]:
        """Определяет способствующие факторы"""

        factors = []
        zones = tension_summary.get('zones', {})

        if injury_type == 'medial_epicondylitis':
            forearm_high = zones.get('forearms', {}).get('high_percent', 0)
            if forearm_high > 30:
                factors.append(f'Хроническое перенапряжение предплечий ({forearm_high:.0f}% времени)')

            asymmetry = zones.get('forearms', {}).get('avg_asymmetry', 0)
            if asymmetry > 15:
                factors.append(f'Асимметричная нагрузка на руки ({asymmetry:.0f})')

        elif injury_type == 'shoulder_impingement':
            shoulder_high = zones.get('shoulders', {}).get('high_percent', 0)
            if shoulder_high > 30:
                factors.append(f'Частое положение рук над головой ({shoulder_high:.0f}% времени)')

        elif injury_type == 'lumbar_strain':
            lumbar_high = zones.get('lumbar', {}).get('high_percent', 0)
            if lumbar_high > 25:
                factors.append(f'Нестабильность кора ({lumbar_high:.0f}% времени)')

        elif injury_type == 'knee_ligament_stress':
            knee_high = zones.get('knees', {}).get('high_percent', 0)
            if knee_high > 20:
                factors.append(f'Критические углы в коленях ({knee_high:.0f}% времени)')

        if not factors:
            factors.append('Общая накопительная нагрузка')

        return factors

    def _get_prevention_measures(self, injury_type: str, risk_level: RiskLevel) -> List[str]:
        """Возвращает меры профилактики"""

        measures = {
            'medial_epicondylitis': [
                'Эксцентрические упражнения для предплечий 3×15 ежедневно',
                'Растяжка сгибателей запястья после тренировок',
                'Контроль силы хвата - не "смертельная хватка"',
                'Массаж предплечий теннисным мячом'
            ],
            'shoulder_impingement': [
                'Мобилизация плечевых суставов 2 раза в день',
                'Укрепление задней дельты и ротаторной манжеты',
                'Коррекция осанки - убрать "круглые плечи"',
                'Растяжка грудных мышц'
            ],
            'lumbar_strain': [
                'Упражнения на укрепление кора ежедневно',
                'Растяжка сгибателей бедра',
                'Контроль положения таза',
                'Техника правильного дыхания под нагрузкой'
            ],
            'knee_ligament_stress': [
                'Укрепление квадрицепсов и задней поверхности бедра',
                'Работа над стабильностью голеностопа',
                'Избегать критических углов (< 50°)',
                'Контролируемые приземления'
            ]
        }

        base_measures = measures.get(injury_type, ['Консультация со специалистом'])

        # Добавляем срочные меры для HIGH/CRITICAL
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            base_measures.insert(0, '⚠️ НЕМЕДЛЕННО снизить нагрузку на 50%')
            base_measures.insert(1, '⚠️ Консультация с врачом/физиотерапевтом')

        return base_measures

    def _get_early_indicators(self, injury_type: str) -> List[str]:
        """Возвращает ранние признаки травмы"""

        indicators = {
            'medial_epicondylitis': [
                'Боль по внутренней стороне локтя при хвате',
                'Утренняя скованность предплечий',
                'Слабость при сжатии кулака',
                'Боль при нажатии на внутренний надмыщелок'
            ],
            'shoulder_impingement': [
                'Боль при поднятии руки выше головы',
                'Ночные боли в плече',
                'Щелчки и хруст в плечевом суставе',
                'Ограничение подвижности'
            ],
            'lumbar_strain': [
                'Утренняя скованность поясницы',
                'Боль при наклонах вперед',
                'Спазмы мышц поясницы',
                'Болезненность при пальпации'
            ],
            'knee_ligament_stress': [
                'Боль внутри колена при нагрузке',
                'Отек после тренировок',
                'Нестабильность колена',
                'Хруст или щелчки'
            ]
        }

        return indicators.get(injury_type, ['Общий дискомфорт в области'])

    def _get_self_test(self, injury_type: str) -> str:
        """Возвращает тест для самодиагностики"""

        tests = {
            'medial_epicondylitis': (
                'Тест сопротивления сгибанию запястья: положите предплечье на стол ладонью вверх, '
                'попросите кого-то надавить на ладонь, пока вы сопротивляетесь сгибанию. '
                'Боль во внутренней части локтя = положительный тест.'
            ),
            'shoulder_impingement': (
                'Тест Нира: поднимите прямую руку вперед и вверх до максимума. '
                'Боль или дискомфорт в плече (особенно в диапазоне 60-120°) = положительный тест.'
            ),
            'lumbar_strain': (
                'Тест наклона вперед: встаньте прямо, медленно наклоняйтесь вперед, пытаясь коснуться пальцев ног. '
                'Боль в пояснице или сильное ограничение движения = положительный тест.'
            ),
            'knee_ligament_stress': (
                'Тест на боль при нагрузке: встаньте на одну ногу, медленно присядьте до угла 90°. '
                'Боль внутри колена или нестабильность = положительный тест.'
            )
        }

        return tests.get(injury_type, 'Консультация со специалистом для диагностики')


def format_injury_predictions(predictions: Dict[str, InjuryPrediction]) -> str:
    """
    Форматирует прогнозы травм для отчета
    """

    if not predictions:
        return "✅ Риски травм не выявлены - продолжай в том же духе!"

    # Сортируем по вероятности
    sorted_predictions = sorted(
        predictions.items(),
        key=lambda x: x[1].probability,
        reverse=True
    )

    # Эмодзи для уровней риска
    risk_emoji = {
        RiskLevel.LOW: '🟢',
        RiskLevel.MODERATE: '🟡',
        RiskLevel.HIGH: '🟠',
        RiskLevel.CRITICAL: '🔴'
    }

    report = "⚠️ ПРЕДСКАЗАНИЕ РИСКОВ ТРАВМ\n\n"

    for injury_type, prediction in sorted_predictions:
        risk_icon = risk_emoji.get(prediction.risk_level, '⚪')

        report += f"{risk_icon} {prediction.injury_type}\n"
        report += f"Зона: {prediction.body_part}\n"
        report += f"Вероятность: {prediction.probability:.0f}%\n"
        report += f"Временные рамки: {prediction.timeline}\n"
        report += f"Тип: {prediction.trauma_type.value}\n\n"

        # Факторы
        if prediction.contributing_factors:
            report += "Причины:\n"
            for factor in prediction.contributing_factors[:2]:  # Топ-2
                report += f"• {factor}\n"
            report += "\n"

        # Профилактика (только топ-2 для краткости)
        report += "Профилактика:\n"
        for measure in prediction.prevention_measures[:2]:
            report += f"• {measure}\n"
        report += "\n"

        # Ранние признаки
        report += "Следи за:\n"
        for indicator in prediction.early_indicators[:2]:
            report += f"• {indicator}\n"
        report += "\n"

        # Самопроверка
        if prediction.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            report += f"🔍 Самопроверка: {prediction.self_test}\n\n"

        report += "━" * 40 + "\n\n"

    return report.strip()
