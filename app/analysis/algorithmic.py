"""
Алгоритмическое описание анализа скалолазания v1.0

Генерирует текстовое описание БЕЗ использования AI,
на основе собранных метрик и данных анализа.

Включает:
- Качество пролаза (%)
- Анализ зажимов и напряжения
- Предиктивная аналитика травм
- Рекомендации по улучшению
"""

import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class AlgorithmicAnalyzer:
    """
    Генератор алгоритмических описаний без AI

    Принимает данные анализа и генерирует человекочитаемое
    описание с рекомендациями.
    """

    def __init__(self):
        # Пороги для оценок
        self.quality_thresholds = {
            'excellent': 85,
            'good': 70,
            'average': 55,
            'needs_work': 40
        }

        # База знаний по зажимам и травмам
        self.tension_risk_map = {
            'левое_плечо': {'injury': 'Импинджмент плеча', 'exercise': 'Растяжка плечевого пояса'},
            'правое_плечо': {'injury': 'Импинджмент плеча', 'exercise': 'Растяжка плечевого пояса'},
            'левый_локоть': {'injury': 'Эпикондилит (локоть скалолаза)', 'exercise': 'Эксцентрические упражнения для предплечья'},
            'правый_локоть': {'injury': 'Эпикондилит (локоть скалолаза)', 'exercise': 'Эксцентрические упражнения для предплечья'},
            'поясница': {'injury': 'Грыжа/протрузия диска', 'exercise': 'Укрепление кора, планка'},
            'левое_колено': {'injury': 'Тендинит надколенника', 'exercise': 'Укрепление квадрицепса'},
            'правое_колено': {'injury': 'Тендинит надколенника', 'exercise': 'Укрепление квадрицепса'}
        }

    def generate_full_description(self, analysis_data: Dict[str, Any]) -> str:
        """
        Генерирует полное алгоритмическое описание

        Args:
            analysis_data: данные из VideoProcessor.process_video()

        Returns:
            str: человекочитаемое описание анализа
        """
        sections = []

        # 1. Общая оценка качества
        sections.append(self._generate_quality_section(analysis_data))

        # 2. Анализ напряжения и зажимов
        sections.append(self._generate_tension_section(analysis_data))

        # 3. Предиктивная аналитика травм
        sections.append(self._generate_injury_section(analysis_data))

        # 4. Анализ движения
        sections.append(self._generate_movement_section(analysis_data))

        # 5. Ключевые рекомендации
        sections.append(self._generate_recommendations(analysis_data))

        return "\n\n".join(filter(None, sections))

    def _generate_quality_section(self, data: Dict[str, Any]) -> str:
        """Секция: Общая оценка качества пролаза"""
        quality = data.get('avg_pose_quality', 0)
        balance = data.get('avg_balance_score', 0)
        intensity = data.get('avg_motion_intensity', 0)

        # Определяем уровень
        if quality >= self.quality_thresholds['excellent']:
            level = "ОТЛИЧНО"
            emoji = "🌟"
            comment = "Техника на высоком уровне!"
        elif quality >= self.quality_thresholds['good']:
            level = "ХОРОШО"
            emoji = "👍"
            comment = "Уверенное лазание с небольшими недочётами."
        elif quality >= self.quality_thresholds['average']:
            level = "СРЕДНЕ"
            emoji = "📊"
            comment = "Есть над чем поработать."
        elif quality >= self.quality_thresholds['needs_work']:
            level = "ТРЕБУЕТ РАБОТЫ"
            emoji = "⚠️"
            comment = "Рекомендую сфокусироваться на базовой технике."
        else:
            level = "НАЧАЛЬНЫЙ"
            emoji = "📚"
            comment = "Начни с основ - это нормально для старта!"

        # Прогресс-бар
        bar_filled = int(quality / 10)
        bar_empty = 10 - bar_filled
        progress_bar = "█" * bar_filled + "░" * bar_empty

        section = f"""
{emoji} КАЧЕСТВО ПРОЛАЗА: {level}
{'═' * 30}

Общая оценка: {progress_bar} {quality:.0f}%

📊 Детализация:
• Качество позы: {quality:.1f}%
• Баланс тела: {balance:.1f}%
• Интенсивность: {intensity:.1f}

💬 {comment}
""".strip()

        return section

    def _generate_tension_section(self, data: Dict[str, Any]) -> str:
        """Секция: Анализ напряжения и зажимов"""
        tension_data = data.get('tension_analysis', {})

        if not tension_data:
            return ""

        tension_index = tension_data.get('overall_tension_index', 0)
        risk_level = tension_data.get('risk_level', 'LOW')
        zones = tension_data.get('zones', {})

        # Эмодзи по уровню риска
        risk_emoji = {
            'LOW': '✅',
            'MODERATE': '🟡',
            'HIGH': '⚠️',
            'CRITICAL': '🔴'
        }.get(risk_level, '❓')

        # Находим проблемные зоны
        problem_zones = []
        for zone_name, zone_data in zones.items():
            if isinstance(zone_data, dict):
                classification = zone_data.get('classification', 'LOW')
                if classification in ['HIGH', 'MODERATE', 'CRITICAL']:
                    problem_zones.append((zone_name, zone_data))

        section = f"""
⚡ АНАЛИЗ НАПРЯЖЕНИЯ
{'═' * 30}

Индекс напряжения: {tension_index:.0f}/100
Уровень риска: {risk_emoji} {risk_level}
"""

        if problem_zones:
            section += "\n🔥 Зоны повышенного напряжения:\n"
            for zone_name, zone_data in problem_zones:
                avg_tension = zone_data.get('avg_tension', 0)
                section += f"• {zone_name}: {avg_tension:.0f}% напряжения\n"

                # Добавляем рекомендацию по зоне
                if zone_name in self.tension_risk_map:
                    exercise = self.tension_risk_map[zone_name]['exercise']
                    section += f"  → Рекомендация: {exercise}\n"
        else:
            section += "\n✅ Все зоны в норме - отличный контроль тела!"

        return section.strip()

    def _generate_injury_section(self, data: Dict[str, Any]) -> str:
        """Секция: Предиктивная аналитика травм"""
        injury_data = data.get('injury_prediction', {})

        if not injury_data:
            return ""

        predictions = injury_data.get('predictions', {})
        overall_risk = injury_data.get('overall_risk', 0)

        if not predictions or overall_risk < 0.2:
            return f"""
🏥 ПРОГНОЗ ТРАВМ
{'═' * 30}

✅ Риск травм минимальный ({overall_risk*100:.0f}%)
Продолжай в том же духе!
""".strip()

        # Сортируем по вероятности
        sorted_predictions = sorted(
            predictions.items(),
            key=lambda x: x[1].get('probability', 0) if isinstance(x[1], dict) else 0,
            reverse=True
        )

        section = f"""
🏥 ПРОГНОЗ ТРАВМ
{'═' * 30}

⚠️ Общий риск: {overall_risk*100:.0f}%

Потенциальные проблемы:
"""

        for injury_type, pred in sorted_predictions[:3]:
            if not isinstance(pred, dict):
                continue

            prob = pred.get('probability', 0)
            if prob < 0.2:
                continue

            risk_level = pred.get('risk_level', 'LOW')
            body_part = pred.get('body_part', 'неизвестно')
            timeline = pred.get('timeline', '')
            prevention = pred.get('prevention_measures', [])

            risk_emoji = {'LOW': '🟢', 'MODERATE': '🟡', 'HIGH': '🟠', 'CRITICAL': '🔴'}.get(risk_level, '⚪')

            section += f"""
{risk_emoji} {injury_type.replace('_', ' ').title()}
   Вероятность: {prob*100:.0f}%
   Зона: {body_part}
"""
            if timeline:
                section += f"   Прогноз: {timeline}\n"
            if prevention:
                section += f"   Профилактика: {prevention[0]}\n"

        return section.strip()

    def _generate_movement_section(self, data: Dict[str, Any]) -> str:
        """Секция: Анализ движения (BoulderVision метрики)"""
        bv_data = data.get('bouldervision', {})

        if not bv_data:
            return ""

        avg_velocity = bv_data.get('avg_velocity_ratio', 1.0)
        total_distance = bv_data.get('total_distance', 0)
        pattern = bv_data.get('movement_pattern', 'unknown')
        time_zones = bv_data.get('time_zones', {})

        # Интерпретация паттерна
        pattern_descriptions = {
            'explosive': '💥 Взрывной стиль - быстрые динамичные движения',
            'smooth': '🌊 Плавный стиль - контролируемые переходы',
            'static': '🧘 Статичный стиль - много пауз и обдумывания',
            'erratic': '⚡ Хаотичный стиль - резкие смены темпа',
            'unknown': '❓ Паттерн не определён'
        }

        section = f"""
🏃 АНАЛИЗ ДВИЖЕНИЯ
{'═' * 30}

Паттерн: {pattern_descriptions.get(pattern, pattern)}

📈 Метрики:
• Коэффициент скорости: {avg_velocity:.2f}
• Общая дистанция: {total_distance:.2f}
"""

        # Распределение по зонам (если есть)
        if time_zones:
            lower = time_zones.get('lower', 0)
            middle = time_zones.get('middle', 0)
            upper = time_zones.get('upper', 0)
            total = lower + middle + upper

            if total > 0:
                section += f"""
📍 Распределение по высоте:
• Нижняя зона: {lower/total*100:.0f}%
• Средняя зона: {middle/total*100:.0f}%
• Верхняя зона: {upper/total*100:.0f}%
"""

        return section.strip()

    def _generate_recommendations(self, data: Dict[str, Any]) -> str:
        """Секция: Ключевые рекомендации"""
        recommendations = []

        quality = data.get('avg_pose_quality', 50)
        balance = data.get('avg_balance_score', 50)
        tension = data.get('tension_analysis', {}).get('overall_tension_index', 0)
        fall_detected = data.get('fall_detected', False)

        # Рекомендации по качеству
        if quality < 60:
            recommendations.append("📚 Работай над базовой техникой: положение тела, хват, постановка ног")
        elif quality < 80:
            recommendations.append("🎯 Сфокусируйся на точности движений и экономии сил")

        # Рекомендации по балансу
        if balance < 50:
            recommendations.append("⚖️ Тренируй баланс: упражнения на одной ноге, планки")
        elif balance < 70:
            recommendations.append("🧘 Добавь упражнения на проприоцепцию и контроль центра масс")

        # Рекомендации по напряжению
        if tension > 60:
            recommendations.append("🧘‍♂️ Высокое напряжение! Добавь растяжку и восстановление между сессиями")
        elif tension > 40:
            recommendations.append("💆 Обрати внимание на зажимы - работай над расслаблением")

        # Рекомендации по падению
        if fall_detected:
            recommendations.append("⚠️ Проанализируй момент падения - что можно улучшить?")

        # Nine-box рекомендации
        nine_box = data.get('nine_box', {})
        if nine_box:
            nb_recs = nine_box.get('recommendations', [])
            recommendations.extend(nb_recs[:2])

        if not recommendations:
            recommendations.append("🌟 Отличная работа! Продолжай тренироваться в том же духе.")

        section = f"""
💡 КЛЮЧЕВЫЕ РЕКОМЕНДАЦИИ
{'═' * 30}
"""
        for i, rec in enumerate(recommendations[:5], 1):
            section += f"\n{i}. {rec}"

        return section.strip()

    def generate_short_summary(self, data: Dict[str, Any]) -> str:
        """
        Генерирует короткую сводку (для превью/уведомлений)

        Returns:
            str: 2-3 строки с ключевой информацией
        """
        quality = data.get('avg_pose_quality', 0)
        fall = data.get('fall_detected', False)
        tension_index = data.get('tension_analysis', {}).get('overall_tension_index', 0)

        # Определяем уровень
        if quality >= 85:
            grade = "🌟 Отлично"
        elif quality >= 70:
            grade = "👍 Хорошо"
        elif quality >= 55:
            grade = "📊 Средне"
        else:
            grade = "📚 Требует работы"

        summary = f"{grade} | Качество: {quality:.0f}%"

        if fall:
            summary += " | ⚠️ Падение"
        elif tension_index > 50:
            summary += " | 🔥 Высокое напряжение"

        return summary

    def get_improvement_areas(self, data: Dict[str, Any]) -> List[str]:
        """
        Возвращает список областей для улучшения

        Returns:
            list: топ-3 области для работы
        """
        areas = []

        quality = data.get('avg_pose_quality', 50)
        balance = data.get('avg_balance_score', 50)
        tension = data.get('tension_analysis', {}).get('overall_tension_index', 0)

        metrics = [
            ('Техника позы', 100 - quality),
            ('Баланс', 100 - balance),
            ('Напряжение', tension)
        ]

        # Сортируем по "проблемности"
        metrics.sort(key=lambda x: x[1], reverse=True)

        for name, score in metrics[:3]:
            if score > 30:
                areas.append(name)

        return areas if areas else ['Поддержание уровня']


def generate_algorithmic_report(analysis_data: Dict[str, Any]) -> str:
    """
    Утилитарная функция для быстрой генерации отчёта

    Args:
        analysis_data: данные анализа

    Returns:
        str: полный алгоритмический отчёт
    """
    analyzer = AlgorithmicAnalyzer()
    return analyzer.generate_full_description(analysis_data)
