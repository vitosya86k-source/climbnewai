"""
AI Рекомендации для скалолазов v1.0

Генерирует персонализированные рекомендации с помощью Claude AI:
- Упражнения для улучшения слабых сторон
- Книги по скалолазанию
- Эксперты и тренеры
- Конкретный план тренировок
"""

import logging
from typing import Dict, Any, List, Optional
import anthropic

from app.config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)


# База знаний: книги по скалолазанию
CLIMBING_BOOKS = {
    'technique': [
        {
            'title': 'The Self-Coached Climber',
            'author': 'Dan Hague, Douglas Hunter',
            'focus': 'Техника движений и самоанализ',
            'level': 'intermediate'
        },
        {
            'title': '9 Out of 10 Climbers Make the Same Mistakes',
            'author': 'Dave MacLeod',
            'focus': 'Распространённые ошибки и их исправление',
            'level': 'all'
        },
        {
            'title': 'The Rock Warrior\'s Way',
            'author': 'Arno Ilgner',
            'focus': 'Психология и ментальная подготовка',
            'level': 'intermediate'
        }
    ],
    'strength': [
        {
            'title': 'Training for Climbing',
            'author': 'Eric Hörst',
            'focus': 'Силовая подготовка и периодизация',
            'level': 'all'
        },
        {
            'title': 'Beastmaking',
            'author': 'Ned Feehally',
            'focus': 'Тренировка пальцев и предплечий',
            'level': 'advanced'
        }
    ],
    'injury_prevention': [
        {
            'title': 'Climb Injury-Free',
            'author': 'Jared Vagy',
            'focus': 'Профилактика травм',
            'level': 'all'
        },
        {
            'title': 'Make or Break',
            'author': 'Dave MacLeod',
            'focus': 'Травмы и восстановление',
            'level': 'all'
        }
    ],
    'beginner': [
        {
            'title': 'Скалолазание. Базовый курс',
            'author': 'Том Хорнбейн',
            'focus': 'Основы для начинающих',
            'level': 'beginner'
        }
    ]
}

# База знаний: известные эксперты/тренеры
CLIMBING_EXPERTS = {
    'technique': [
        {
            'name': 'Neil Gresham',
            'specialty': 'Техника и движение',
            'resource': 'YouTube канал "Neil Gresham Masterclass"',
            'country': 'UK'
        },
        {
            'name': 'Adam Ondra',
            'specialty': 'Соревновательное лазание',
            'resource': 'YouTube канал "Adam Ondra"',
            'country': 'Czech Republic'
        }
    ],
    'training': [
        {
            'name': 'Eric Hörst',
            'specialty': 'Тренировочные методики',
            'resource': 'trainingforclimbing.com',
            'country': 'USA'
        },
        {
            'name': 'Lattice Training',
            'specialty': 'Научный подход к тренировкам',
            'resource': 'latticetraining.com',
            'country': 'UK'
        }
    ],
    'injury': [
        {
            'name': 'Dr. Jared Vagy (The Climbing Doctor)',
            'specialty': 'Травмы и реабилитация',
            'resource': 'theclimbingdoctor.com',
            'country': 'USA'
        }
    ],
    'mental': [
        {
            'name': 'Hazel Findlay',
            'specialty': 'Психология и страх',
            'resource': 'YouTube, подкасты',
            'country': 'UK'
        }
    ]
}

# База упражнений по категориям
EXERCISES_DATABASE = {
    'balance': [
        {
            'name': 'Планка на одной руке',
            'description': 'Удержание планки поочерёдно на каждой руке по 20-30 сек',
            'sets': '3 подхода на каждую сторону',
            'benefit': 'Укрепление кора и стабилизаторов'
        },
        {
            'name': 'Стойка на одной ноге',
            'description': 'Стоять на одной ноге с закрытыми глазами',
            'sets': '3x30 сек на каждую ногу',
            'benefit': 'Проприоцепция и баланс'
        },
        {
            'name': 'Траверс с флагами',
            'description': 'Траверс на боулдеринге с обязательным флагом на каждом перехвате',
            'sets': '5-10 минут',
            'benefit': 'Контроль центра масс'
        }
    ],
    'finger_strength': [
        {
            'name': 'Висы на фингерборде',
            'description': 'Повторяющиеся висы на 20мм зацепке: 7 сек вис, 3 сек отдых',
            'sets': '6 повторений, 3 подхода',
            'benefit': 'Сила хвата и выносливость пальцев'
        },
        {
            'name': 'Эксцентрические упражнения',
            'description': 'Медленное разгибание пальцев с резинкой',
            'sets': '3x15 на каждую руку',
            'benefit': 'Профилактика локтя скалолаза'
        }
    ],
    'shoulder': [
        {
            'name': 'Вращения плеча с резинкой',
            'description': 'Внешняя и внутренняя ротация плеча с сопротивлением',
            'sets': '3x15 на каждую сторону',
            'benefit': 'Стабилизация плечевого сустава'
        },
        {
            'name': 'Y-T-W подъёмы',
            'description': 'Лёжа на животе, подъёмы рук в формах Y, T и W',
            'sets': '3x10 каждой формы',
            'benefit': 'Укрепление ротаторной манжеты'
        }
    ],
    'core': [
        {
            'name': 'Скручивания на турнике',
            'description': 'Подъём коленей к груди в висе',
            'sets': '3x10-15',
            'benefit': 'Сила кора для нависаний'
        },
        {
            'name': 'Боковая планка с подъёмом бедра',
            'description': 'В боковой планке опускать и поднимать бедро',
            'sets': '3x12 на каждую сторону',
            'benefit': 'Косые мышцы и стабилизация'
        }
    ],
    'flexibility': [
        {
            'name': 'Растяжка "лягушка"',
            'description': 'Широкая стойка на коленях, опускание таза к полу',
            'sets': '3x45 сек',
            'benefit': 'Раскрытие бёдер для хайстепов'
        },
        {
            'name': 'Растяжка плечевого пояса',
            'description': 'Рука за спиной, тянуть локоть противоположной рукой',
            'sets': '3x30 сек на каждую сторону',
            'benefit': 'Подвижность плеч'
        }
    ],
    'footwork': [
        {
            'name': 'Тихие ноги',
            'description': 'Лазать траверс, ставя ноги абсолютно бесшумно',
            'sets': '10-15 минут',
            'benefit': 'Точность постановки ног'
        },
        {
            'name': 'Одно касание',
            'description': 'Поставить ногу на зацеп с первого раза, без перестановки',
            'sets': 'Целая сессия',
            'benefit': 'Внимательность и точность'
        }
    ]
}


class AIRecommendationEngine:
    """
    Генератор AI рекомендаций для скалолазов

    Использует Claude API для персонализированных советов,
    дополненных базой знаний по книгам, экспертам и упражнениям.
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

    def generate_recommendations(
        self,
        analysis_data: Dict[str, Any],
        climber_name: str = "Скалолаз",
        focus_areas: List[str] = None
    ) -> Dict[str, Any]:
        """
        Генерирует полный набор рекомендаций

        Args:
            analysis_data: данные анализа из VideoProcessor
            climber_name: имя для персонализации
            focus_areas: области фокуса (если не указаны, определяются автоматически)

        Returns:
            dict с рекомендациями по упражнениям, книгам, экспертам
        """
        # Определяем области для улучшения
        if not focus_areas:
            focus_areas = self._identify_focus_areas(analysis_data)

        result = {
            'focus_areas': focus_areas,
            'exercises': self._get_exercises(focus_areas, analysis_data),
            'books': self._get_books(focus_areas),
            'experts': self._get_experts(focus_areas),
            'training_plan': None,
            'ai_insights': None
        }

        # Генерируем AI инсайты если доступен API
        if self.client:
            try:
                result['ai_insights'] = self._generate_ai_insights(
                    analysis_data, focus_areas, climber_name
                )
                result['training_plan'] = self._generate_training_plan(
                    analysis_data, focus_areas
                )
            except Exception as e:
                logger.warning(f"AI рекомендации недоступны: {e}")

        return result

    def _identify_focus_areas(self, data: Dict[str, Any]) -> List[str]:
        """Определяет области для улучшения на основе данных"""
        areas = []

        quality = data.get('avg_pose_quality', 50)
        balance = data.get('avg_balance_score', 50)
        tension = data.get('tension_analysis', {}).get('overall_tension_index', 0)
        injury_risk = data.get('injury_prediction', {}).get('overall_risk', 0)

        # Анализ слабых сторон
        if balance < 60:
            areas.append('balance')
        if quality < 60:
            areas.append('technique')
        if tension > 50:
            areas.append('tension_release')
        if injury_risk > 0.3:
            areas.append('injury_prevention')

        # Анализ напряжённых зон
        tension_zones = data.get('tension_analysis', {}).get('zones', {})
        for zone_name, zone_data in tension_zones.items():
            if isinstance(zone_data, dict):
                if zone_data.get('classification') in ['HIGH', 'CRITICAL']:
                    if 'плечо' in zone_name.lower():
                        areas.append('shoulder')
                    elif 'локоть' in zone_name.lower():
                        areas.append('finger_strength')  # Связано с хватом
                    elif 'поясница' in zone_name.lower():
                        areas.append('core')

        # Если всё хорошо - работаем над силой и гибкостью
        if not areas:
            areas = ['strength', 'flexibility']

        return list(set(areas))[:4]  # Максимум 4 области

    def _get_exercises(self, focus_areas: List[str], data: Dict[str, Any]) -> List[Dict]:
        """Подбирает упражнения по областям фокуса"""
        exercises = []

        area_mapping = {
            'balance': 'balance',
            'technique': 'footwork',
            'tension_release': 'flexibility',
            'injury_prevention': 'shoulder',
            'shoulder': 'shoulder',
            'finger_strength': 'finger_strength',
            'core': 'core',
            'strength': 'finger_strength',
            'flexibility': 'flexibility'
        }

        added_categories = set()
        for area in focus_areas:
            category = area_mapping.get(area)
            if category and category not in added_categories:
                category_exercises = EXERCISES_DATABASE.get(category, [])
                exercises.extend(category_exercises[:2])  # По 2 упражнения на категорию
                added_categories.add(category)

        return exercises[:6]  # Максимум 6 упражнений

    def _get_books(self, focus_areas: List[str]) -> List[Dict]:
        """Подбирает книги по областям фокуса"""
        books = []

        area_mapping = {
            'balance': 'technique',
            'technique': 'technique',
            'tension_release': 'injury_prevention',
            'injury_prevention': 'injury_prevention',
            'shoulder': 'injury_prevention',
            'finger_strength': 'strength',
            'core': 'strength',
            'strength': 'strength',
            'flexibility': 'technique'
        }

        added_books = set()
        for area in focus_areas:
            category = area_mapping.get(area)
            if category:
                category_books = CLIMBING_BOOKS.get(category, [])
                for book in category_books:
                    if book['title'] not in added_books:
                        books.append(book)
                        added_books.add(book['title'])

        return books[:3]  # Максимум 3 книги

    def _get_experts(self, focus_areas: List[str]) -> List[Dict]:
        """Подбирает экспертов по областям фокуса"""
        experts = []

        area_mapping = {
            'balance': 'technique',
            'technique': 'technique',
            'tension_release': 'injury',
            'injury_prevention': 'injury',
            'shoulder': 'injury',
            'finger_strength': 'training',
            'core': 'training',
            'strength': 'training',
            'flexibility': 'technique',
            'mental': 'mental'
        }

        added_experts = set()
        for area in focus_areas:
            category = area_mapping.get(area)
            if category:
                category_experts = CLIMBING_EXPERTS.get(category, [])
                for expert in category_experts:
                    if expert['name'] not in added_experts:
                        experts.append(expert)
                        added_experts.add(expert['name'])

        return experts[:3]  # Максимум 3 эксперта

    def _generate_ai_insights(
        self,
        data: Dict[str, Any],
        focus_areas: List[str],
        climber_name: str
    ) -> str:
        """Генерирует персональные инсайты через Claude"""
        if not self.client:
            return None

        prompt = f"""Ты опытный тренер по скалолазанию. Проанализируй данные и дай краткие, конкретные советы.

ДАННЫЕ АНАЛИЗА:
- Качество позы: {data.get('avg_pose_quality', 0):.1f}%
- Баланс: {data.get('avg_balance_score', 0):.1f}%
- Индекс напряжения: {data.get('tension_analysis', {}).get('overall_tension_index', 0):.0f}/100
- Риск травм: {data.get('injury_prediction', {}).get('overall_risk', 0)*100:.0f}%
- Падение: {'Да' if data.get('fall_detected') else 'Нет'}

ОБЛАСТИ ДЛЯ РАБОТЫ: {', '.join(focus_areas)}

Дай 3 конкретных совета для {climber_name}.
Каждый совет: 1-2 предложения, практичный, можно применить сразу.
Без общих фраз типа "продолжай тренироваться".

Формат:
1. [совет]
2. [совет]
3. [совет]"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Ошибка Claude API: {e}")
            return None

    def _generate_training_plan(
        self,
        data: Dict[str, Any],
        focus_areas: List[str]
    ) -> Optional[str]:
        """Генерирует краткий план тренировок через Claude"""
        if not self.client:
            return None

        prompt = f"""Составь КРАТКИЙ недельный план тренировок для скалолаза.

ТЕКУЩИЙ УРОВЕНЬ:
- Качество техники: {data.get('avg_pose_quality', 0):.0f}%
- Баланс: {data.get('avg_balance_score', 0):.0f}%

ФОКУС: {', '.join(focus_areas)}

Дай план на неделю в формате:
Пн: [активность, 30-60 мин]
Вт: [активность]
...

Максимум 5 тренировок, 1-2 дня отдыха. Краткий формат, без лишних объяснений."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Ошибка генерации плана: {e}")
            return None

    def format_recommendations(self, recommendations: Dict[str, Any]) -> str:
        """Форматирует рекомендации в читаемый текст"""
        sections = []

        # Области фокуса
        focus = recommendations.get('focus_areas', [])
        focus_names = {
            'balance': 'Баланс',
            'technique': 'Техника',
            'tension_release': 'Снятие напряжения',
            'injury_prevention': 'Профилактика травм',
            'shoulder': 'Плечевой пояс',
            'finger_strength': 'Сила пальцев',
            'core': 'Кор',
            'strength': 'Сила',
            'flexibility': 'Гибкость'
        }
        focus_translated = [focus_names.get(f, f) for f in focus]

        sections.append(f"""
🎯 ОБЛАСТИ РАЗВИТИЯ
{'═' * 30}
{', '.join(focus_translated)}
""")

        # Упражнения
        exercises = recommendations.get('exercises', [])
        if exercises:
            ex_text = "\n💪 РЕКОМЕНДУЕМЫЕ УПРАЖНЕНИЯ\n" + "═" * 30 + "\n"
            for i, ex in enumerate(exercises, 1):
                ex_text += f"""
{i}. {ex['name']}
   {ex['description']}
   📊 {ex['sets']}
   ✨ {ex['benefit']}
"""
            sections.append(ex_text)

        # Книги
        books = recommendations.get('books', [])
        if books:
            books_text = "\n📚 КНИГИ ДЛЯ ИЗУЧЕНИЯ\n" + "═" * 30 + "\n"
            for book in books:
                books_text += f"""
• "{book['title']}"
  Автор: {book['author']}
  Фокус: {book['focus']}
"""
            sections.append(books_text)

        # Эксперты
        experts = recommendations.get('experts', [])
        if experts:
            exp_text = "\n👨‍🏫 ЭКСПЕРТЫ И РЕСУРСЫ\n" + "═" * 30 + "\n"
            for expert in experts:
                exp_text += f"""
• {expert['name']}
  Специализация: {expert['specialty']}
  Ресурс: {expert['resource']}
"""
            sections.append(exp_text)

        # AI инсайты
        ai_insights = recommendations.get('ai_insights')
        if ai_insights:
            sections.append(f"""
🤖 ПЕРСОНАЛЬНЫЕ СОВЕТЫ (AI)
{'═' * 30}
{ai_insights}
""")

        # План тренировок
        plan = recommendations.get('training_plan')
        if plan:
            sections.append(f"""
📅 ПЛАН НА НЕДЕЛЮ
{'═' * 30}
{plan}
""")

        return "\n".join(sections).strip()


def get_ai_recommendations(analysis_data: Dict[str, Any], climber_name: str = "Скалолаз") -> str:
    """
    Утилитарная функция для получения форматированных AI рекомендаций

    Args:
        analysis_data: данные анализа
        climber_name: имя скалолаза

    Returns:
        str: форматированные рекомендации
    """
    engine = AIRecommendationEngine()
    recommendations = engine.generate_recommendations(analysis_data, climber_name)
    return engine.format_recommendations(recommendations)
