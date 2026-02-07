"""Сравнение пользователя с базой спортсменов"""

import logging
from typing import Dict, Any, List, Tuple

from .athlete_database import ATHLETE_DATABASE, get_level_numeric, get_level_name_ru

logger = logging.getLogger(__name__)


def find_similar_athletes(analysis_data: Dict[str, Any], top_n: int = 3) -> List[Dict[str, Any]]:
    """
    Находит наиболее похожих спортсменов из базы
    
    Сравнение по:
    - Качество позы (главный фактор)
    - Интенсивность движений
    - Уровень (±1)
    """
    user_quality = analysis_data.get('avg_pose_quality', 0)
    user_intensity = analysis_data.get('avg_motion_intensity', 0)
    
    # Определяем уровень пользователя
    user_level = determine_user_level(user_quality)
    user_level_numeric = get_level_numeric(user_level)
    
    logger.info(f"Определен уровень пользователя: {user_level} (качество: {user_quality:.1f}%)")
    
    # Ищем похожих спортсменов
    similarities = []
    
    for athlete_id, athlete_data in ATHLETE_DATABASE.items():
        # Фильтруем по уровню (±1)
        athlete_level_numeric = get_level_numeric(athlete_data['level'])
        if abs(athlete_level_numeric - user_level_numeric) > 1:
            continue
        
        # Вычисляем similarity score
        similarity = calculate_similarity(
            user_quality,
            user_intensity,
            athlete_data['avg_quality'],
            athlete_data['avg_intensity']
        )
        
        similarities.append({
            'athlete_id': athlete_id,
            'athlete_data': athlete_data,
            'similarity': similarity
        })
    
    # Сортируем по убыванию similarity
    similarities.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Возвращаем топ-N
    result = similarities[:top_n]
    
    logger.info(f"Найдено {len(result)} похожих спортсменов")
    for item in result:
        logger.info(f"  - {item['athlete_data']['name']}: {item['similarity']:.1f}% сходства")
    
    return result


def determine_user_level(avg_quality: float) -> str:
    """Определяет уровень пользователя на основе качества позы"""
    if avg_quality >= 90:
        return "pro"
    elif avg_quality >= 80:
        return "advanced"
    elif avg_quality >= 65:
        return "intermediate"
    else:
        return "beginner"


def calculate_similarity(
    user_quality: float,
    user_intensity: float,
    athlete_quality: float,
    athlete_intensity: float
) -> float:
    """
    Вычисляет процент схожести (0-100)
    
    Веса:
    - Качество позы: 70%
    - Интенсивность: 30%
    """
    # Разница в качестве (0-100)
    quality_diff = abs(user_quality - athlete_quality)
    quality_similarity = max(0, 100 - quality_diff)
    
    # Разница в интенсивности (обычно 0-40, нормализуем)
    intensity_diff = abs(user_intensity - athlete_intensity)
    intensity_similarity = max(0, 100 - (intensity_diff * 2.5))  # Масштабируем
    
    # Взвешенная сумма
    total_similarity = (quality_similarity * 0.7) + (intensity_similarity * 0.3)
    
    return round(total_similarity, 1)


def format_comparison(
    similar_athletes: List[Dict[str, Any]],
    user_quality: float
) -> str:
    """Форматирует блок сравнения для отчета"""
    
    if not similar_athletes:
        return "Недостаточно данных для сравнения"
    
    user_level = determine_user_level(user_quality)
    user_level_ru = get_level_name_ru(user_level)
    
    # Определяем процентиль
    percentile = calculate_percentile(user_quality)
    
    result = f"""
🏆 СРАВНЕНИЕ С БАЗОЙ СПОРТСМЕНОВ
----------------------------------------
ВАШ УРОВЕНЬ: {user_level_ru} (топ {percentile}%)

ПОХОЖИЕ СПОРТСМЕНЫ:
"""
    
    for i, item in enumerate(similar_athletes, 1):
        athlete = item['athlete_data']
        similarity = item['similarity']
        
        result += f"""
{i}. {athlete['name']} - {similarity}% сходства
   Стиль: {get_style_ru(athlete['style'])}
   Специализация: {athlete['specialty']}
   Сильные стороны: {', '.join(athlete['strengths'])}
"""
    
    # Добавляем инсайт
    top_athlete = similar_athletes[0]['athlete_data']
    insight = generate_insight(top_athlete, user_quality)
    
    result += f"""
💡 ИНСАЙТ:
{insight}

ПРОГНОЗ РОСТА:
При регулярных тренировках (3-4 раза в неделю) ожидается улучшение 
на {estimate_growth_rate(user_quality):.1f}% за месяц.
"""
    
    return result.strip()


def calculate_percentile(quality: float) -> int:
    """Вычисляет процентиль пользователя"""
    if quality >= 90:
        return 5  # Топ 5%
    elif quality >= 80:
        return 15  # Топ 15%
    elif quality >= 70:
        return 35  # Топ 35%
    elif quality >= 60:
        return 60  # Топ 60%
    else:
        return 80  # Топ 80%


def get_style_ru(style: str) -> str:
    """Перевод стиля на русский"""
    styles = {
        "technical": "Технический",
        "dynamic": "Динамичный",
        "versatile": "Универсальный",
        "speed": "Скоростной",
        "power": "Силовой",
        "endurance": "Выносливый",
        "learning": "Обучающийся",
        "developing": "Развивающийся",
        "building": "Строящий базу",
        "progressing": "Прогрессирующий",
        "foundation": "Фундаментальный",
        "basics": "Базовый"
    }
    return styles.get(style, style)


def generate_insight(top_athlete: Dict[str, Any], user_quality: float) -> str:
    """Генерирует инсайт на основе топ-спортсмена"""
    style = get_style_ru(top_athlete['style'])
    specialty = top_athlete['specialty'].lower()
    
    improvement = top_athlete['avg_quality'] - user_quality
    
    if improvement > 10:
        insight = f"""Спортсмены с похожим {style.lower()} стилем улучшили технику на 15-20% за 2 месяца,
работая над {specialty} и добавив специализированные тренировки."""
    elif improvement > 0:
        insight = f"""Ты близок к уровню спортсменов с {style.lower()} стилем!
Продолжай фокусироваться на {specialty} - ты на правильном пути."""
    else:
        insight = f"""Отличные результаты! Твой {style.lower()} стиль на высоком уровне.
Для дальнейшего роста попробуй выйти из зоны комфорта и поработать над другими аспектами."""
    
    return insight


def estimate_growth_rate(current_quality: float) -> float:
    """Оценивает ожидаемый рост качества за месяц"""
    if current_quality < 60:
        return 8.0  # Новички растут быстрее
    elif current_quality < 75:
        return 5.0  # Средний темп
    elif current_quality < 85:
        return 3.0  # Замедление роста
    else:
        return 1.5  # Профи растут медленно


