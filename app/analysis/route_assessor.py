"""
Модуль для персонализированной оценки сложности трасс

Определяет:
- Соответствие трассы уровню скалолаза (разминка, рабочий уровень, проект)
- Факторы-бутылочные горлышки
- Готовность к следующему уровню
- Персонализированные рекомендации для прогресса

Интеграция:
- nine_box_model: позиция скалолаза (навыки × физика × психика)
- tension_analyzer: текущая усталость и напряжение
- injury_predictor: риски травм
- BoulderVision: эффективность движения
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class RouteLevel(Enum):
    """Уровни сложности трасс (французская шкала для боулдеринга)"""
    V0 = "3"        # Начинающий
    V1 = "4"
    V2 = "5a"
    V3 = "5b"       # Средний уровень
    V4 = "5c"
    V5 = "6a"
    V6 = "6b"       # Продвинутый
    V7 = "6c"
    V8 = "7a"
    V9 = "7b"       # Эксперт
    V10 = "7c"
    V11 = "8a"
    V12 = "8b"      # Элита
    V13 = "8c"
    V14 = "9a"
    V15_PLUS = "9a+" # Топ мира


class RouteAssessmentType(Enum):
    """Тип оценки трассы относительно уровня скалолаза"""
    WARMUP = "warmup"              # Разминка (на 2+ уровня легче)
    WORKING = "working"            # Рабочий уровень (на 0-1 уровень легче)
    PROJECT = "project"            # Проект (на уровне или +1)
    STRETCH_GOAL = "stretch_goal"  # Растяжка (+2-3 уровня)
    TOO_HARD = "too_hard"          # Слишком сложно (+4 и более)


class BottleneckFactor(Enum):
    """Факторы, ограничивающие прохождение трассы"""
    TECHNICAL_SKILLS = "technical_skills"     # Недостаток техники
    POWER = "power"                           # Недостаток силы
    ENDURANCE = "endurance"                   # Недостаток выносливости
    FLEXIBILITY = "flexibility"               # Недостаток гибкости
    MENTAL = "mental"                         # Психологический фактор
    INJURY_RISK = "injury_risk"               # Высокий риск травмы
    FATIGUE = "fatigue"                       # Усталость
    BODY_TENSION = "body_tension"             # Зажимы в теле
    ROUTE_READING = "route_reading"           # Чтение трассы
    BETA_EXECUTION = "beta_execution"         # Исполнение беты


@dataclass
class RouteAssessment:
    """Результат оценки трассы для конкретного скалолаза"""

    # Основная оценка
    assessment_type: RouteAssessmentType
    route_level: str                      # Уровень трассы (например, "6b")
    climber_max_level: str                # Максимальный уровень скалолаза
    difficulty_gap: int                   # Разница в уровнях (-2, 0, +3, и т.д.)

    # Воспринимаемая сложность
    perceived_difficulty: float           # 0-10, где 10 = максимально сложно
    completion_probability: float         # 0-100% вероятность прохождения

    # Bottleneck анализ
    primary_bottleneck: BottleneckFactor
    secondary_bottleneck: Optional[BottleneckFactor]
    bottleneck_scores: Dict[str, float]   # Оценки для каждого фактора (0-10)

    # Готовность к прогрессу
    readiness_for_next_level: float       # 0-100%, готовность к следующему уровню
    recommended_training_focus: List[str] # Что тренировать в первую очередь

    # Персонализированные рекомендации
    recommendations: List[str]
    warning_signs: List[str]              # Предупреждения (усталость, травмы)

    # Контекст
    nine_box_position: Optional[str]      # Позиция в 9-box модели
    injury_risks_summary: Optional[str]   # Краткая сводка рисков травм


class RouteAssessor:
    """
    Оценщик трасс с персонализацией под конкретного скалолаза

    Учитывает:
    - Максимальный уровень и опыт скалолаза
    - Текущее состояние (9-box модель)
    - Риски травм и усталость
    - Эффективность движения
    """

    # Маппинг V-grades в числа для сравнения
    GRADE_TO_NUMBER = {
        "3": 0, "4": 1, "5a": 2, "5b": 3, "5c": 4,
        "6a": 5, "6b": 6, "6c": 7, "7a": 8, "7b": 9,
        "7c": 10, "8a": 11, "8b": 12, "8c": 13, "9a": 14, "9a+": 15
    }

    NUMBER_TO_GRADE = {v: k for k, v in GRADE_TO_NUMBER.items()}

    def __init__(self):
        """Инициализация оценщика трасс"""
        logger.info("RouteAssessor инициализирован")

    def assess_route(
        self,
        route_grade: str,
        climber_max_grade: str,
        video_analysis: Dict[str, Any],
        climber_profile: Optional[Dict[str, Any]] = None
    ) -> RouteAssessment:
        """
        Оценивает трассу для конкретного скалолаза

        Args:
            route_grade: Уровень трассы (например, "6b")
            climber_max_grade: Максимальный уровень скалолаза
            video_analysis: Результаты анализа видео со всеми модулями
            climber_profile: Профиль скалолаза (опыт, травмы, цели)

        Returns:
            RouteAssessment с полной оценкой
        """
        logger.info(f"Оценка трассы {route_grade} для скалолаза уровня {climber_max_grade}")

        # Конвертируем grade в числа
        route_num = self.GRADE_TO_NUMBER.get(route_grade, 5)
        climber_num = self.GRADE_TO_NUMBER.get(climber_max_grade, 5)
        difficulty_gap = route_num - climber_num

        # Определяем тип оценки
        assessment_type = self._determine_assessment_type(difficulty_gap)

        # Воспринимаемая сложность
        perceived_difficulty = self._calculate_perceived_difficulty(
            difficulty_gap, video_analysis
        )

        completion_probability = self._calculate_completion_probability(
            difficulty_gap, video_analysis, perceived_difficulty
        )

        # Bottleneck анализ
        bottleneck_scores = self._analyze_bottlenecks(video_analysis, climber_profile)
        primary_bottleneck, secondary_bottleneck = self._identify_top_bottlenecks(
            bottleneck_scores
        )

        # Готовность к следующему уровню
        readiness = self._calculate_readiness_for_next_level(
            difficulty_gap, bottleneck_scores, video_analysis
        )

        # Фокус тренировок
        training_focus = self._recommend_training_focus(bottleneck_scores, primary_bottleneck)

        # Рекомендации
        recommendations = self._generate_recommendations(
            assessment_type, difficulty_gap, bottleneck_scores,
            video_analysis, readiness
        )

        # Предупреждения
        warnings = self._generate_warnings(video_analysis, bottleneck_scores)

        # Контекст
        nine_box_position = video_analysis.get('nine_box', {}).get('category', 'UNKNOWN')
        injury_risks = self._summarize_injury_risks(video_analysis)

        return RouteAssessment(
            assessment_type=assessment_type,
            route_level=route_grade,
            climber_max_level=climber_max_grade,
            difficulty_gap=difficulty_gap,
            perceived_difficulty=perceived_difficulty,
            completion_probability=completion_probability,
            primary_bottleneck=primary_bottleneck,
            secondary_bottleneck=secondary_bottleneck,
            bottleneck_scores=bottleneck_scores,
            readiness_for_next_level=readiness,
            recommended_training_focus=training_focus,
            recommendations=recommendations,
            warning_signs=warnings,
            nine_box_position=nine_box_position,
            injury_risks_summary=injury_risks
        )

    def _determine_assessment_type(self, difficulty_gap: int) -> RouteAssessmentType:
        """Определяет тип оценки трассы"""
        if difficulty_gap <= -2:
            return RouteAssessmentType.WARMUP
        elif difficulty_gap in [-1, 0]:
            return RouteAssessmentType.WORKING
        elif difficulty_gap in [1, 2]:
            return RouteAssessmentType.PROJECT
        elif difficulty_gap == 3:
            return RouteAssessmentType.STRETCH_GOAL
        else:
            return RouteAssessmentType.TOO_HARD

    def _calculate_perceived_difficulty(
        self,
        difficulty_gap: int,
        video_analysis: Dict[str, Any]
    ) -> float:
        """
        Рассчитывает воспринимаемую сложность (0-10)

        Учитывает не только gap, но и:
        - Насколько плавно двигается
        - Сколько попыток было
        - Уровень напряжения
        """
        # Базовая сложность от gap
        base_difficulty = min(10, max(0, 5 + difficulty_gap * 1.5))

        # Корректировки от анализа видео
        adjustments = 0.0

        # Velocity ratio (плавность движения)
        bv = video_analysis.get('bouldervision', {})
        velocity_ratio = bv.get('avg_velocity_ratio', 1.0)
        if velocity_ratio > 2.0:  # Рывки = сложнее
            adjustments += 1.0
        elif velocity_ratio < 1.3:  # Плавно = легче
            adjustments -= 0.5

        # Tension (зажимы = сложнее)
        tension = video_analysis.get('tension_analysis', {})
        tension_index = tension.get('overall_tension_index', 0)
        if tension_index > 65:
            adjustments += 1.5
        elif tension_index < 35:
            adjustments -= 0.5

        # Падение (если было = значит сложно)
        if video_analysis.get('fall_detected', False):
            adjustments += 1.0

        # Nine-box position
        nine_box_score = video_analysis.get('nine_box', {}).get('skill_score', 5)
        if nine_box_score < 4:  # Низкие навыки = субъективно сложнее
            adjustments += 0.5

        perceived = base_difficulty + adjustments
        return min(10.0, max(0.0, perceived))

    def _calculate_completion_probability(
        self,
        difficulty_gap: int,
        video_analysis: Dict[str, Any],
        perceived_difficulty: float
    ) -> float:
        """Рассчитывает вероятность прохождения трассы (0-100%)"""

        # Базовая вероятность от gap
        if difficulty_gap <= -2:
            base_prob = 95
        elif difficulty_gap == -1:
            base_prob = 85
        elif difficulty_gap == 0:
            base_prob = 70
        elif difficulty_gap == 1:
            base_prob = 50
        elif difficulty_gap == 2:
            base_prob = 30
        elif difficulty_gap == 3:
            base_prob = 15
        else:
            base_prob = 5

        # Корректировки
        adjustments = 0

        # Падение снижает вероятность
        if video_analysis.get('fall_detected', False):
            adjustments -= 15

        # Высокое напряжение = быстрая усталость
        tension = video_analysis.get('tension_analysis', {})
        if tension.get('overall_tension_index', 0) > 70:
            adjustments -= 10

        # Риски травм
        injury = video_analysis.get('injury_prediction', {})
        high_risk_count = sum(
            1 for pred in injury.get('predictions', {}).values()
            if pred.get('risk_level') in ['HIGH', 'CRITICAL']
        )
        adjustments -= high_risk_count * 5

        # Nine-box position (высокие скиллы повышают шанс)
        nine_box = video_analysis.get('nine_box', {})
        skill_score = nine_box.get('skill_score', 5)
        if skill_score >= 7:
            adjustments += 10
        elif skill_score <= 3:
            adjustments -= 10

        probability = base_prob + adjustments
        return min(100.0, max(0.0, probability))

    def _analyze_bottlenecks(
        self,
        video_analysis: Dict[str, Any],
        climber_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Анализирует факторы-бутылочные горлышки

        Возвращает словарь {фактор: оценка_проблемности (0-10)}
        где 10 = серьезная проблема, 0 = не проблема
        """
        scores = {}

        # 1. Technical Skills (от 9-box и velocity_ratio)
        nine_box = video_analysis.get('nine_box', {})
        skill_score = nine_box.get('skill_score', 5)
        scores['technical_skills'] = max(0, 10 - skill_score)

        # 2. Power (от physical_score и peak velocity)
        physical_score = nine_box.get('physical_score', 5)
        scores['power'] = max(0, 10 - physical_score)

        # 3. Endurance (от time zones и distance)
        bv = video_analysis.get('bouldervision', {})
        time_zones = bv.get('time_zones', {'lower': 0, 'middle': 0, 'upper': 0})
        upper_time = time_zones.get('upper', 0)
        if upper_time < 20:  # Мало времени наверху = нехватка выносливости
            scores['endurance'] = 7.0
        else:
            scores['endurance'] = 3.0

        # 4. Flexibility (от углов суставов в tension_analyzer)
        tension = video_analysis.get('tension_analysis', {})
        zones = tension.get('zones', {})
        flexibility_issues = sum(
            1 for zone_data in zones.values()
            if zone_data.get('classification') == 'HIGH'
        )
        scores['flexibility'] = min(10, flexibility_issues * 2.5)

        # 5. Mental (от mental_score в 9-box)
        mental_score = nine_box.get('mental_score', 5)
        scores['mental'] = max(0, 10 - mental_score)

        # 6. Injury Risk (от injury_predictor)
        injury = video_analysis.get('injury_prediction', {})
        high_risk_count = sum(
            1 for pred in injury.get('predictions', {}).values()
            if pred.get('risk_level') in ['HIGH', 'CRITICAL']
        )
        scores['injury_risk'] = min(10, high_risk_count * 3.0)

        # 7. Fatigue (от tension overall_tension_index)
        tension_index = tension.get('overall_tension_index', 0)
        scores['fatigue'] = min(10, tension_index / 10)

        # 8. Body Tension (зажимы)
        scores['body_tension'] = min(10, tension_index / 10)

        # 9. Route Reading (от движения - если много рывков)
        velocity_ratio = bv.get('avg_velocity_ratio', 1.0)
        if velocity_ratio > 2.5:
            scores['route_reading'] = 7.0
        elif velocity_ratio > 2.0:
            scores['route_reading'] = 5.0
        else:
            scores['route_reading'] = 2.0

        # 10. Beta Execution (от падения и velocity)
        if video_analysis.get('fall_detected', False):
            scores['beta_execution'] = 8.0
        elif velocity_ratio > 2.0:
            scores['beta_execution'] = 6.0
        else:
            scores['beta_execution'] = 3.0

        return scores

    def _identify_top_bottlenecks(
        self,
        bottleneck_scores: Dict[str, float]
    ) -> tuple[BottleneckFactor, Optional[BottleneckFactor]]:
        """Определяет 1-2 главных бутылочных горлышка"""
        sorted_factors = sorted(
            bottleneck_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        primary = BottleneckFactor(sorted_factors[0][0])
        secondary = BottleneckFactor(sorted_factors[1][0]) if len(sorted_factors) > 1 else None

        return primary, secondary

    def _calculate_readiness_for_next_level(
        self,
        difficulty_gap: int,
        bottleneck_scores: Dict[str, float],
        video_analysis: Dict[str, Any]
    ) -> float:
        """
        Рассчитывает готовность к следующему уровню (0-100%)

        Считается только если текущая трасса = working или warmup
        """
        if difficulty_gap > 0:
            # Если это уже проект/stretch goal, до следующего уровня далеко
            return max(0, 30 - difficulty_gap * 10)

        # Базовая готовность
        base_readiness = 70 if difficulty_gap == 0 else 50

        # Корректировки от bottlenecks
        avg_bottleneck = sum(bottleneck_scores.values()) / len(bottleneck_scores)
        bottleneck_penalty = avg_bottleneck * 5  # До -50%

        # Корректировки от 9-box
        nine_box = video_analysis.get('nine_box', {})
        if nine_box.get('skill_score', 5) >= 7:
            base_readiness += 10
        if nine_box.get('physical_score', 5) >= 7:
            base_readiness += 10

        # Риски травм
        injury = video_analysis.get('injury_prediction', {})
        critical_risk = any(
            pred.get('risk_level') == 'CRITICAL'
            for pred in injury.get('predictions', {}).values()
        )
        if critical_risk:
            base_readiness -= 30

        readiness = base_readiness - bottleneck_penalty
        return min(100.0, max(0.0, readiness))

    def _recommend_training_focus(
        self,
        bottleneck_scores: Dict[str, float],
        primary_bottleneck: BottleneckFactor
    ) -> List[str]:
        """Рекомендует фокус тренировок"""
        recommendations = []

        # Топ-3 проблемы
        sorted_factors = sorted(
            bottleneck_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        for factor_name, score in sorted_factors:
            if score < 3:  # Не проблема
                continue

            factor = BottleneckFactor(factor_name)

            if factor == BottleneckFactor.TECHNICAL_SKILLS:
                recommendations.append("Техника: отработка базовых движений на легких трассах")
            elif factor == BottleneckFactor.POWER:
                recommendations.append("Сила: кампусборд, силовые движения, максимальные хваты")
            elif factor == BottleneckFactor.ENDURANCE:
                recommendations.append("Выносливость: длинные траверсы, 4x4, ARC training")
            elif factor == BottleneckFactor.FLEXIBILITY:
                recommendations.append("Гибкость: стретчинг, йога, разминка с упором на проблемные зоны")
            elif factor == BottleneckFactor.MENTAL:
                recommendations.append("Психология: работа со страхом падений, дыхательные практики")
            elif factor == BottleneckFactor.BODY_TENSION:
                recommendations.append("Расслабление: учиться отдыхать на трассе, shake-outs, дыхание")
            elif factor == BottleneckFactor.ROUTE_READING:
                recommendations.append("Чтение трасс: наблюдение за опытными, разбор бет, проговаривание последовательности")

        return recommendations[:3]  # Максимум 3 рекомендации

    def _generate_recommendations(
        self,
        assessment_type: RouteAssessmentType,
        difficulty_gap: int,
        bottleneck_scores: Dict[str, float],
        video_analysis: Dict[str, Any],
        readiness: float
    ) -> List[str]:
        """Генерирует персонализированные рекомендации"""
        recommendations = []

        # По типу оценки
        if assessment_type == RouteAssessmentType.WARMUP:
            recommendations.append("✅ Отличная трасса для разминки - используй для отработки техники")
        elif assessment_type == RouteAssessmentType.WORKING:
            recommendations.append("💪 Хороший рабочий уровень - фокусируйся на чистоте исполнения")
        elif assessment_type == RouteAssessmentType.PROJECT:
            recommendations.append("🎯 Отличный проект - разбей на секции, тренируй движения отдельно")
        elif assessment_type == RouteAssessmentType.STRETCH_GOAL:
            recommendations.append("🚀 Амбициозная цель - попробуй отдельные движения, не стремись пройти сразу")
        else:  # TOO_HARD
            recommendations.append("⚠️ Трасса пока слишком сложная - вернись через пару месяцев тренировок")

        # По readiness
        if readiness >= 80 and difficulty_gap <= 0:
            recommendations.append("🎓 Ты готов пробовать трассы следующего уровня!")
        elif readiness >= 60 and difficulty_gap <= 0:
            recommendations.append("📈 Близко к следующему уровню - усиль тренировки по слабым местам")

        # По tension
        tension = video_analysis.get('tension_analysis', {})
        if tension.get('overall_tension_index', 0) > 65:
            recommendations.append("😌 Учись расслаблять мышцы на трассе - это сэкономит силы")

        # По падениям
        if video_analysis.get('fall_detected', False):
            fall_analysis = video_analysis.get('fall_analysis', {})
            if fall_analysis.get('fall_type') == 'controlled':
                recommendations.append("👍 Хорошо контролируешь падение - продолжай в том же духе")
            else:
                recommendations.append("⚠️ Работай над безопасными падениями")

        return recommendations[:4]  # Максимум 4 рекомендации

    def _generate_warnings(
        self,
        video_analysis: Dict[str, Any],
        bottleneck_scores: Dict[str, float]
    ) -> List[str]:
        """Генерирует предупреждающие знаки"""
        warnings = []

        # Риски травм
        injury = video_analysis.get('injury_prediction', {})
        for injury_type, pred in injury.get('predictions', {}).items():
            risk_level = pred.get('risk_level', 'LOW')
            if risk_level in ['HIGH', 'CRITICAL']:
                timeline = pred.get('timeline', 'неизвестно')
                warnings.append(
                    f"⚠️ Риск {injury_type}: {risk_level} (прогноз: {timeline})"
                )

        # Усталость
        if bottleneck_scores.get('fatigue', 0) > 7:
            warnings.append("😴 Признаки усталости - рекомендуется отдых")

        # Зажимы
        if bottleneck_scores.get('body_tension', 0) > 7:
            tension = video_analysis.get('tension_analysis', {})
            problem_zones = [
                name for name, data in tension.get('zones', {}).items()
                if data.get('classification') == 'HIGH'
            ]
            if problem_zones:
                zones_str = ', '.join(problem_zones)
                warnings.append(f"🔥 Сильные зажимы в: {zones_str}")

        return warnings

    def _summarize_injury_risks(self, video_analysis: Dict[str, Any]) -> str:
        """Создает краткую сводку рисков травм"""
        injury = video_analysis.get('injury_prediction', {})
        predictions = injury.get('predictions', {})

        if not predictions:
            return "Нет значимых рисков"

        risk_counts = {'LOW': 0, 'MODERATE': 0, 'HIGH': 0, 'CRITICAL': 0}
        for pred in predictions.values():
            risk_level = pred.get('risk_level', 'LOW')
            risk_counts[risk_level] += 1

        parts = []
        if risk_counts['CRITICAL'] > 0:
            parts.append(f"⛔ {risk_counts['CRITICAL']} критических")
        if risk_counts['HIGH'] > 0:
            parts.append(f"⚠️ {risk_counts['HIGH']} высоких")
        if risk_counts['MODERATE'] > 0:
            parts.append(f"🟡 {risk_counts['MODERATE']} умеренных")

        return ', '.join(parts) if parts else "Низкие риски"

    def get_grade_progression(self, current_grade: str) -> List[str]:
        """Возвращает следующие 3 уровня для прогрессии"""
        current_num = self.GRADE_TO_NUMBER.get(current_grade, 5)
        progression = []
        for i in range(1, 4):
            next_num = current_num + i
            if next_num in self.NUMBER_TO_GRADE:
                progression.append(self.NUMBER_TO_GRADE[next_num])
        return progression

    def format_assessment_report(self, assessment: RouteAssessment) -> str:
        """Форматирует assessment в читаемый текстовый отчет"""
        report_lines = [
            "=" * 50,
            "🎯 ОЦЕНКА ТРАССЫ",
            "=" * 50,
            "",
            f"📍 Трасса: {assessment.route_level}",
            f"👤 Ваш максимум: {assessment.climber_max_level}",
            f"📊 Разница: {assessment.difficulty_gap:+d} уровней",
            "",
            f"🎭 Тип: {assessment.assessment_type.value.upper()}",
            f"💭 Воспринимаемая сложность: {assessment.perceived_difficulty:.1f}/10",
            f"🎲 Вероятность прохождения: {assessment.completion_probability:.0f}%",
            "",
            "🔍 АНАЛИЗ BOTTLENECKS:",
            f"Основная проблема: {assessment.primary_bottleneck.value}",
        ]

        if assessment.secondary_bottleneck:
            report_lines.append(f"Вторая проблема: {assessment.secondary_bottleneck.value}")

        report_lines.extend([
            "",
            f"📈 Готовность к следующему уровню: {assessment.readiness_for_next_level:.0f}%",
            "",
            "💡 РЕКОМЕНДАЦИИ:",
        ])

        for rec in assessment.recommendations:
            report_lines.append(f"  • {rec}")

        if assessment.recommended_training_focus:
            report_lines.extend([
                "",
                "🎯 ФОКУС ТРЕНИРОВОК:",
            ])
            for focus in assessment.recommended_training_focus:
                report_lines.append(f"  • {focus}")

        if assessment.warning_signs:
            report_lines.extend([
                "",
                "⚠️ ПРЕДУПРЕЖДЕНИЯ:",
            ])
            for warning in assessment.warning_signs:
                report_lines.append(f"  • {warning}")

        report_lines.extend([
            "",
            f"📍 9-Box позиция: {assessment.nine_box_position}",
            f"🏥 Риски травм: {assessment.injury_risks_summary}",
            "",
            "=" * 50,
        ])

        return "\n".join(report_lines)
