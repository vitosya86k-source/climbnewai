"""Выбор эксперта на основе данных анализа"""

import random
import logging
from typing import Dict, Any

from .expert_profiles import EXPERTS

logger = logging.getLogger(__name__)


def select_expert(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Выбирает 1 из 4 экспертов на основе анализа видео
    
    Логика выбора:
    - Качество >= 80: Magnus или Eric (позитивная оценка)
    - Качество 60-80: Neil или Dave (развивающий совет)
    - Падение обнаружено: Neil или Dave (анализ проблем)
    - Качество < 60: Magnus или Eric (критика с мотивацией)
    """
    avg_quality = analysis_data.get('avg_pose_quality', 0)
    fall_detected = analysis_data.get('fall_detected', False)
    
    # Логика выбора
    if fall_detected:
        # При падении - тактический или систематический подход
        expert_name = random.choice(['Neil Gresham', 'Dave MacLeod'])
        logger.info(f"Падение обнаружено -> выбран {expert_name}")
    
    elif avg_quality >= 80:
        # Высокое качество - позитивная динамическая или эффективная оценка
        expert_name = random.choice(['Magnus Midtbø', 'Eric Hörst'])
        logger.info(f"Высокое качество ({avg_quality:.1f}%) -> выбран {expert_name}")
    
    elif avg_quality >= 60:
        # Среднее качество - тактические или системные советы
        expert_name = random.choice(['Neil Gresham', 'Dave MacLeod'])
        logger.info(f"Среднее качество ({avg_quality:.1f}%) -> выбран {expert_name}")
    
    else:
        # Низкое качество - мотивирующая критика
        expert_name = random.choice(['Magnus Midtbø', 'Eric Hörst'])
        logger.info(f"Низкое качество ({avg_quality:.1f}%) -> выбран {expert_name}")
    
    expert_profile = EXPERTS[expert_name].copy()
    
    # Генерируем оценку эксперта (0-100)
    expert_score = calculate_expert_score(analysis_data, expert_name)
    expert_profile['score'] = expert_score
    
    # Выбираем случайный совет
    expert_profile['selected_advice'] = random.choice(expert_profile['signature_advice'])
    
    return expert_profile


def calculate_expert_score(analysis_data: Dict[str, Any], expert_name: str) -> float:
    """
    Вычисляет оценку эксперта на основе его специализации
    
    - Magnus: динамика + плавность
    - Eric: эффективность + техника
    - Neil: тактика + адаптивность
    - Dave: общий прогресс + методичность
    """
    avg_quality = analysis_data.get('avg_pose_quality', 0)
    avg_intensity = analysis_data.get('avg_motion_intensity', 0)
    fall_detected = analysis_data.get('fall_detected', False)
    
    base_score = avg_quality
    
    if expert_name == "Magnus Midtbø":
        # Magnus ценит динамику и флоу
        if avg_intensity > 20:
            base_score += 5
        if not fall_detected:
            base_score += 3
    
    elif expert_name == "Eric Hörst":
        # Eric ценит эффективность (низкая интенсивность при высоком качестве)
        if avg_quality > 70 and avg_intensity < 20:
            base_score += 8
        elif avg_intensity < 15:
            base_score += 5
    
    elif expert_name == "Neil Gresham":
        # Neil смотрит на общую картину и адаптацию
        if not fall_detected and avg_quality > 65:
            base_score += 5
        # Если есть падение, но пытался адаптироваться
        if fall_detected:
            base_score -= 10
    
    elif expert_name == "Dave MacLeod":
        # Dave оценивает системный подход
        base_score = avg_quality  # Базовая оценка
        # Dave более строгий, но справедливый
        if avg_quality > 75:
            base_score += 3
    
    # Ограничиваем диапазон 0-100
    return max(0, min(100, base_score))


def get_expert_comment_context(expert_profile: Dict[str, Any], analysis_data: Dict[str, Any]) -> str:
    """
    Создает контекст для комментария эксперта
    """
    name = expert_profile['name']
    score = expert_profile['score']
    specialization = expert_profile['specialization']
    selected_advice = expert_profile['selected_advice']
    
    context = f"""
🎯 {name} ({specialization})
Оценка: {score:.0f}/100

{selected_advice}
"""
    
    return context.strip()


