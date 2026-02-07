"""
9-Box модель для оценки скалолаза
Три измерения: Навыки | Физические возможности | Психология
"""

import numpy as np
from typing import Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class ClimberNineBoxModel:
    """
    9-Box модель для комплексной оценки скалолаза

    Оси:
    - X: Физические возможности (Physical Capacity) - 0-10
    - Y: Технические навыки (Technical Skills) - 0-10
    - Z: Психологическое состояние (Mental State) - 0-10
    """

    # Определения всех 27 категорий (3x3x3)
    # Для простоты используем 9 основных (фиксируя mental на confident)
    BOX_DEFINITIONS = {
        # Топ-право: Высокие навыки + Сильная физика
        ('high', 'high', 'confident'): {
            'category': 'ELITE_STAR',
            'label': '⭐ Элитный скалолаз',
            'description': 'Высокий уровень во всех аспектах',
            'recommendations': [
                'Сложные проектные трассы (+2-3 категории)',
                'Участие в соревнованиях',
                'Наставничество новичков'
            ]
        },

        # Высокие навыки + Средняя физика
        ('high', 'medium', 'confident'): {
            'category': 'TECHNICAL_MASTER',
            'label': '🧠 Технический мастер',
            'description': 'Отличная техника компенсирует недостаток силы',
            'recommendations': [
                'Силовые тренировки (campus board, hangboard)',
                'Продолжать техническую работу на плитах',
                'Постепенно увеличивать overh ang'
            ]
        },

        # Высокие навыки + Слабая физика
        ('high', 'low', 'confident'): {
            'category': 'TECHNIQUE_VETERAN',
            'label': '🎯 Ветеран техники',
            'description': 'Опыт и техника есть, но физика подводит',
            'recommendations': [
                'Акцент на общую физподготовку',
                'Силовой цикл 6-8 недель',
                'Технические трассы для поддержания уровня'
            ]
        },

        # Средние навыки + Высокая физика
        ('medium', 'high', 'confident'): {
            'category': 'POWER_CLIMBER',
            'label': '💪 Силовой скалолаз',
            'description': 'Сильный физически, техника требует работы',
            'recommendations': [
                'Техническая работа на плитах и вертикалях',
                'Упражнения на footwork',
                'Видеоанализ для осознания ошибок'
            ]
        },

        # Средние навыки + Средняя физика
        ('medium', 'medium', 'confident'): {
            'category': 'BALANCED_DEVELOPER',
            'label': '⚖️ Развивающийся универсал',
            'description': 'Сбалансированное развитие во всех направлениях',
            'recommendations': [
                'Комплексные тренировки',
                'Разнообразие трасс',
                'Постепенный прогресс'
            ]
        },

        # Средние навыки + Слабая физика
        ('medium', 'low', 'confident'): {
            'category': 'TECHNIQUE_FOCUSED',
            'label': '🎨 Технический новичок',
            'description': 'Понимает технику, но не хватает сил',
            'recommendations': [
                'Базовая физподготовка',
                'Простые трассы с фокусом на качество',
                'Регулярность важнее интенсивности'
            ]
        },

        # Низкие навыки + Высокая физика
        ('low', 'high', 'confident'): {
            'category': 'RAW_POWER',
            'label': '🔥 Сырая сила',
            'description': 'Сильный но неопытный - потенциал огромен!',
            'recommendations': [
                'Базовая техника скалолазания (курс)',
                'Работа над footwork и балансом',
                'Не форсировать сложность - избежать травм'
            ]
        },

        # Низкие навыки + Средняя физика
        ('low', 'medium', 'confident'): {
            'category': 'MOTIVATED_BEGINNER',
            'label': '🌱 Мотивированный новичок',
            'description': 'Начинающий с хорошим потенциалом',
            'recommendations': [
                'Базовые техники',
                'Регулярные тренировки 2-3 раза в неделю',
                'Не гнаться за сложностью'
            ]
        },

        # Низкие навыки + Слабая физика
        ('low', 'low', 'confident'): {
            'category': 'ABSOLUTE_BEGINNER',
            'label': '👶 Абсолютный новичок',
            'description': 'Только начинаешь путь - это нормально!',
            'recommendations': [
                'Вводный курс скалолазания',
                'Общая физподготовка',
                'Первые месяцы - привыкание к нагрузкам'
            ]
        },

        # ANXIOUS варианты (нерешительность)
        ('high', 'high', 'anxious'): {
            'category': 'ANXIOUS_PRO',
            'label': '😰 Тревожный профи',
            'description': 'Навыки есть, но психология мешает',
            'recommendations': [
                'Работа с психологом/ментальным тренером',
                'Практика падений на верхнюю страховку',
                'Медитация и дыхательные практики'
            ]
        },

        ('medium', 'medium', 'anxious'): {
            'category': 'STRUGGLING_CLIMBER',
            'label': '😟 Борющийся скалолаз',
            'description': 'Физика и техника есть, но страхи блокируют',
            'recommendations': [
                'Психологическая работа',
                'Постепенное повышение комфортной зоны',
                'Поддержка сообщества/партнера'
            ]
        },

        ('low', 'high', 'anxious'): {
            'category': 'HIGH_RISK_STRONG',
            'label': '⚠️ Риск травмы',
            'description': 'Сильный но неопытный + тревожность = опасно',
            'recommendations': [
                'НЕМЕДЛЕННО снизить интенсивность',
                'Работа с тренером обязательна',
                'Психологическая поддержка'
            ]
        },
    }

    def assess_climber(
        self,
        video_analysis: Dict,
        user_profile: Dict
    ) -> Dict[str, Any]:
        """
        Оценивает скалолаза по 9-box модели

        Returns:
            {
                'box_category': 'TECHNICAL_MASTER',
                'label': '🧠 Технический мастер',
                'position': {'skill': 'high', 'physical': 'medium', 'mental': 'confident'},
                'scores': {'skill': 8.2, 'physical': 6.5, 'mental': 7.8},
                'description': '...',
                'recommendations': [...],
                'ascii_plot': '...'  # Визуализация
            }
        """

        # 1. Оценка технических навыков (0-10)
        skill_score = self._assess_technical_skills(video_analysis)

        # 2. Оценка физических возможностей (0-10)
        physical_score = self._assess_physical_capacity(video_analysis, user_profile)

        # 3. Оценка психологического состояния (0-10)
        mental_score = self._assess_mental_state(video_analysis)

        # 4. Определяем категорию (low/medium/high)
        skill_cat = self._score_to_category(skill_score)
        physical_cat = self._score_to_category(physical_score)
        mental_cat = 'confident' if mental_score >= 5.5 else 'anxious'

        # 5. Получаем определение бокса
        box_key = (skill_cat, physical_cat, mental_cat)
        box_info = self.BOX_DEFINITIONS.get(
            box_key,
            self.BOX_DEFINITIONS[('medium', 'medium', 'confident')]  # fallback
        )

        # 6. ASCII визуализация
        ascii_plot = self._create_ascii_plot(skill_score, physical_score, mental_score)

        return {
            'box_category': box_info['category'],
            'label': box_info['label'],
            'description': box_info['description'],
            'position': {
                'skill': skill_cat,
                'physical': physical_cat,
                'mental': mental_cat
            },
            'scores': {
                'skill': skill_score,
                'physical': physical_score,
                'mental': mental_score
            },
            'recommendations': box_info['recommendations'],
            'ascii_plot': ascii_plot
        }

    def _assess_technical_skills(self, analysis: Dict) -> float:
        """
        Оценка технических навыков (0-10)

        Факторы:
        - Trajectory efficiency
        - Straight arms efficiency
        - Movement pattern quality
        - Balance score
        - Velocity consistency
        """

        bv = analysis.get('bouldervision', {})

        # 1. Эффективность траектории (0-3 балла)
        traj_eff = bv.get('trajectory_efficiency', 0.5)
        traj_score = traj_eff * 3

        # 2. Эффективность прямых рук (0-3 балла)
        arms_eff = bv.get('straight_arms_efficiency', 0.5)
        arms_score = arms_eff * 3

        # 3. Стабильность velocity (0-2 балла)
        velocity_std = bv.get('velocity_std', 1.0)
        stability_score = max(0, 2 - velocity_std)

        # 4. Balance score (0-2 балла)
        balance = analysis.get('avg_balance_score', 50) / 50
        balance_score = min(2, balance)

        total = traj_score + arms_score + stability_score + balance_score

        return round(min(10, max(0, total)), 1)

    def _assess_physical_capacity(self, analysis: Dict, user_profile: Dict) -> float:
        """
        Оценка физических возможностей (0-10)

        Факторы:
        - Velocity ratio (скорость)
        - Total distance
        - Time zones distribution
        - Fatigue rate
        - User profile (опыт, возраст)
        """

        bv = analysis.get('bouldervision', {})

        # 1. Скорость (0-3 балла)
        avg_vr = bv.get('avg_velocity_ratio', 1.0)
        velocity_score = min(3, avg_vr * 1.5)

        # 2. Выносливость - низкая скорость усталости (0-3 балла)
        fatigue_data = analysis.get('fatigue_analysis', {})
        fatigue_rate = abs(fatigue_data.get('fatigue_rate', 0))
        endurance_score = max(0, 3 - fatigue_rate * 10)

        # 3. Распределение времени - больше времени наверху = лучше (0-2 балла)
        time_zones = bv.get('time_zones', {})
        upper_time = time_zones.get('upper', 0)
        zone_score = min(2, upper_time / 25)

        # 4. Бонус за опыт из профиля (0-2 балла)
        experience_years = user_profile.get('experience_years', 0)
        experience_score = min(2, experience_years / 3)

        total = velocity_score + endurance_score + zone_score + experience_score

        return round(min(10, max(0, total)), 1)

    def _assess_mental_state(self, analysis: Dict) -> float:
        """
        Оценка психологического состояния (0-10)

        Факторы:
        - Movement pattern (hesitant vs confident)
        - Velocity variability
        - Fall analysis
        - Decision time
        """

        bv = analysis.get('bouldervision', {})

        # 1. Паттерн движения (0-4 балла)
        pattern = bv.get('movement_pattern', 'unknown')
        pattern_scores = {
            'dynamic_consistent': 4.0,
            'steady_pace': 3.5,
            'slow_controlled': 3.0,
            'variable': 2.0,
            'hesitant': 1.0,
            'explosive_bursts': 2.5,
            'unknown': 2.0
        }
        pattern_score = pattern_scores.get(pattern, 2.0)

        # 2. Консистентность - низкая вариативность = уверенность (0-3 балла)
        velocity_std = bv.get('velocity_std', 0.5)
        consistency_score = max(0, 3 - velocity_std * 3)

        # 3. Падения - нет падений = уверен (0-2 балла)
        fall_detected = analysis.get('fall_detected', False)
        fall_score = 0 if fall_detected else 2

        # 4. Скорость принятия решений (0-1 балл)
        avg_vr = bv.get('avg_velocity_ratio', 1.0)
        decision_score = min(1, avg_vr / 1.5) if avg_vr > 0.7 else 0.5

        total = pattern_score + consistency_score + fall_score + decision_score

        return round(min(10, max(0, total)), 1)

    def _score_to_category(self, score: float) -> str:
        """Конвертирует числовой score в категорию"""
        if score >= 7.0:
            return 'high'
        elif score >= 4.0:
            return 'medium'
        else:
            return 'low'

    def _create_ascii_plot(self, skill: float, physical: float, mental: float) -> str:
        """
        Создает ASCII визуализацию позиции в 9-box
        """

        # Нормализуем к 3x3 сетке
        skill_pos = int((skill / 10) * 2)  # 0, 1, 2
        physical_pos = int((physical / 10) * 2)

        # Эмодзи для mental state
        mental_icon = '😊' if mental >= 5.5 else '😰'

        # Создаем сетку
        grid = [
            ['  ', '  ', '  '],
            ['  ', '  ', '  '],
            ['  ', '  ', '  ']
        ]

        # Ставим маркер (y координата инвертирована)
        grid[2 - skill_pos][physical_pos] = mental_icon

        # Форматируем
        plot = f"""
        Физика →
    LOW  MID  HIGH
   ┌────┬────┬────┐
H  │ {grid[2][0]} │ {grid[2][1]} │ {grid[2][2]} │ ↑
   ├────┼────┼────┤ │
M  │ {grid[1][0]} │ {grid[1][1]} │ {grid[1][2]} │ Навыки
   ├────┼────┼────┤ │
L  │ {grid[0][0]} │ {grid[0][1]} │ {grid[0][2]} │
   └────┴────┴────┘

Твоя позиция: {mental_icon}
Навыки: {skill:.1f}/10
Физика: {physical:.1f}/10
Психология: {mental:.1f}/10 {'😊 Уверен' if mental >= 5.5 else '😰 Тревожен'}
"""
        return plot


def format_nine_box_report(assessment: Dict) -> str:
    """
    Форматирует 9-box оценку для отчета
    """

    report = f"""
🎯 9-BOX ОЦЕНКА СКАЛОЛАЗА

{assessment['label']}

📊 ТВОЯ ПОЗИЦИЯ:
{assessment['ascii_plot']}

📝 ОПИСАНИЕ:
{assessment['description']}

💡 РЕКОМЕНДАЦИИ:
"""

    for i, rec in enumerate(assessment['recommendations'], 1):
        report += f"{i}. {rec}\n"

    # Добавляем интерпретацию
    scores = assessment['scores']
    position = assessment['position']

    report += f"""
📈 ДЕТАЛЬНАЯ ОЦЕНКА:

Технические навыки: {scores['skill']:.1f}/10 ({position['skill'].upper()})
"""

    # Интерпретация навыков
    if scores['skill'] >= 7.0:
        report += "   ✅ Отличная техника - продолжай\n"
    elif scores['skill'] >= 4.0:
        report += "   📚 Техника развивается - есть куда расти\n"
    else:
        report += "   📖 Базовая техника - фокус на обучение\n"

    report += f"\nФизические возможности: {scores['physical']:.1f}/10 ({position['physical'].upper()})\n"

    if scores['physical'] >= 7.0:
        report += "   💪 Отличная физика\n"
    elif scores['physical'] >= 4.0:
        report += "   🏋️ Средний уровень - можно усилить\n"
    else:
        report += "   🌱 Развивай силу и выносливость\n"

    report += f"\nПсихологическое состояние: {scores['mental']:.1f}/10\n"

    if scores['mental'] >= 7.0:
        report += "   😊 Уверенность на высоте\n"
    elif scores['mental'] >= 5.5:
        report += "   😐 Стабильное состояние\n"
    else:
        report += "   😰 Есть тревожность - работай над ментальной частью\n"

    return report.strip()
