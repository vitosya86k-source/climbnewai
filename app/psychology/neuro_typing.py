"""Определение нейротипа скалолаза"""

import logging
from typing import Dict, Any

from .profiles import NEURO_TYPES

logger = logging.getLogger(__name__)


def determine_neuro_type(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Определяет нейротип на основе данных анализа
    
    Логика:
    - ФИЛОСОФ: высокая техника, низкая интенсивность
    - ВОИН: средняя техника, высокая интенсивность
    - АНАЛИТИК: очень высокая техника, средняя интенсивность
    - СПРИНТЕР: средняя техника, очень высокая интенсивность
    """
    avg_quality = analysis_data.get('avg_pose_quality', 0)
    avg_intensity = analysis_data.get('avg_motion_intensity', 0)
    fall_detected = analysis_data.get('fall_detected', False)
    
    # Определяем нейротип
    if avg_quality > 85 and 15 < avg_intensity < 25:
        neuro_type_name = "АНАЛИТИК"
        reason = f"Очень высокая техника ({avg_quality:.1f}%) + средняя интенсивность"
    
    elif avg_quality > 80 and avg_intensity < 20:
        neuro_type_name = "ФИЛОСОФ"
        reason = f"Высокая техника ({avg_quality:.1f}%) + низкая интенсивность"
    
    elif avg_quality > 70 and avg_intensity > 25:
        neuro_type_name = "ВОИН"
        reason = f"Хорошая техника + высокая интенсивность ({avg_intensity:.1f})"
    
    elif avg_intensity > 30:
        neuro_type_name = "СПРИНТЕР"
        reason = f"Очень высокая интенсивность ({avg_intensity:.1f})"
    
    else:
        # По умолчанию - ФИЛОСОФ
        neuro_type_name = "ФИЛОСОФ"
        reason = "Сбалансированный подход"
    
    logger.info(f"Определен нейротип: {neuro_type_name} ({reason})")
    
    # Получаем профиль
    profile = NEURO_TYPES[neuro_type_name].copy()
    
    # Добавляем динамические характеристики
    profile['confidence_level'] = calculate_confidence(analysis_data)
    profile['adaptability'] = calculate_adaptability(analysis_data)
    
    return profile


def calculate_confidence(analysis_data: Dict[str, Any]) -> float:
    """Вычисляет уровень уверенности (0-100)"""
    avg_quality = analysis_data.get('avg_pose_quality', 0)
    fall_detected = analysis_data.get('fall_detected', False)
    
    confidence = avg_quality
    
    # Падение снижает уверенность
    if fall_detected:
        confidence -= 15
    
    # Высокая интенсивность может означать как уверенность, так и напряжение
    avg_intensity = analysis_data.get('avg_motion_intensity', 0)
    if avg_intensity > 25:
        confidence -= 5  # Возможно, слишком напряжен
    
    return max(0, min(100, confidence))


def calculate_adaptability(analysis_data: Dict[str, Any]) -> float:
    """Вычисляет способность к адаптации (0-100)"""
    avg_quality = analysis_data.get('avg_pose_quality', 0)
    fall_detected = analysis_data.get('fall_detected', False)
    
    # Базовая адаптивность основана на качестве
    adaptability = avg_quality * 0.8
    
    # Если был срыв, но качество всё равно высокое - хорошая адаптация
    if fall_detected and avg_quality > 70:
        adaptability += 10
    
    # Низкая интенсивность при хорошем качестве = хорошая адаптация
    avg_intensity = analysis_data.get('avg_motion_intensity', 0)
    if avg_quality > 70 and avg_intensity < 20:
        adaptability += 15
    
    return max(0, min(100, adaptability))


def format_neuro_profile(profile: Dict[str, Any]) -> str:
    """Форматирует психологический профиль для отчета"""
    name = profile['name']
    emoji = profile['emoji']
    traits = profile['traits']
    
    vector = profile['profile_vector']
    vector_text = f"СИЛА: {vector['сила']}% | УРАВНОВЕШЕННОСТЬ: {vector['уравновешенность']}% | ПОДВИЖНОСТЬ: {vector['подвижность']}% | ДИНАМИЧНОСТЬ: {vector['динамичность']}%"
    
    stress_behavior = "\n".join([f"• {b}" for b in profile['stress_behavior']])
    stress_triggers = "\n".join([f"• {t}" for t in profile['stress_triggers']])
    
    confidence = profile.get('confidence_level', 0)
    adaptability = profile.get('adaptability', 0)
    
    result = f"""
🧠 ПСИХОЛОГИЧЕСКИЙ ПРОФИЛЬ
----------------------------------------
НЕЙРОТИП: {emoji} {name}
ХАРАКТЕРИСТИКИ: {traits}

ПРОФИЛЬ: {vector_text}

ПОВЕДЕНИЕ В СТРЕССЕ:
{stress_behavior}

ЧТО ВВОДИТ В СТРЕСС:
{stress_triggers}

ПСИХОЛОГИЧЕСКИЕ ХАРАКТЕРИСТИКИ:
• Стиль обучения: {profile['learning_style']}
• Реакция на стресс: {profile['stress_resistance']}
• Подход к решению: {profile['problem_solving']}
• Тип мотивации: {profile['motivation_type']}

УРОВЕНЬ УВЕРЕННОСТИ: {confidence:.1f}%
СПОСОБНОСТЬ К АДАПТАЦИИ: {adaptability:.1f}%

{profile['description']}
"""
    
    return result.strip()


