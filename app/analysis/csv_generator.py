"""Генерация CSV отчетов с реалистичными оценками"""

import csv
import logging
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_csv_report(
    frame_data: List[Dict[str, Any]],
    output_path: Path
) -> str:
    """
    Генерирует CSV отчет с покадровым анализом
    
    ВАЖНО: Реалистичные оценки! Не "превосходно" при 52%
    """
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'Кадр',
                'Время (с)',
                'Качество позы (%)',
                'Интенсивность',
                'Баланс (%)',
                'Оценка',
                'Комментарий'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for frame in frame_data:
                if not frame.get('valid'):
                    continue
                
                quality = frame['pose_quality']
                intensity = frame.get('motion_intensity', 0)
                balance = frame['balance_score']
                
                # РЕАЛИСТИЧНАЯ оценка
                assessment = get_realistic_assessment(quality)
                comment = get_realistic_comment(quality, intensity, balance, frame.get('angles', {}))
                
                writer.writerow({
                    'Кадр': frame['frame_number'],
                    'Время (с)': f"{frame['timestamp']:.2f}",
                    'Качество позы (%)': f"{quality:.1f}",
                    'Интенсивность': f"{intensity:.1f}",
                    'Баланс (%)': f"{balance:.1f}",
                    'Оценка': assessment,
                    'Комментарий': comment
                })
        
        logger.info(f"CSV отчет сохранен: {output_path}")
        return str(output_path)
    
    except Exception as e:
        logger.error(f"Ошибка генерации CSV: {e}")
        raise


def get_realistic_assessment(quality: float) -> str:
    """
    РЕАЛИСТИЧНАЯ оценка качества
    
    НЕТ "превосходно" при 52%!
    """
    if quality >= 90:
        return "Отлично"
    elif quality >= 80:
        return "Хорошо"
    elif quality >= 70:
        return "Удовлетворительно"
    elif quality >= 60:
        return "Посредственно"
    elif quality >= 50:
        return "Слабо"
    elif quality >= 40:
        return "Плохо"
    else:
        return "Критично"


def get_realistic_comment(
    quality: float,
    intensity: float,
    balance: float,
    angles: Dict[str, float]
) -> str:
    """
    РЕАЛИСТИЧНЫЙ комментарий на основе метрик
    """
    comments = []
    
    # Оценка качества
    if quality >= 90:
        comments.append("Отличная техника")
    elif quality >= 80:
        comments.append("Хорошая форма")
    elif quality >= 70:
        comments.append("Приемлемая техника")
    elif quality >= 60:
        comments.append("Техника требует улучшения")
    elif quality >= 50:
        comments.append("Слабая техника")
    elif quality >= 40:
        comments.append("Плохая техника")
    else:
        comments.append("Критическая нестабильность")
    
    # Оценка интенсивности
    if intensity > 30:
        comments.append("очень высокая нагрузка")
    elif intensity > 25:
        comments.append("высокая интенсивность")
    elif intensity > 15:
        comments.append("средняя активность")
    elif intensity > 5:
        comments.append("низкая активность")
    else:
        comments.append("статика")
    
    # Оценка баланса
    if balance < 40:
        comments.append("нестабильный баланс")
    elif balance < 60:
        comments.append("неустойчивое положение")
    
    # Проблемы с углами
    if angles:
        problematic = []
        for joint, angle in angles.items():
            if angle < 60:
                problematic.append(f"перегрузка {joint}")
            elif angle > 150:
                problematic.append(f"недостаточное сгибание {joint}")
        
        if problematic:
            comments.append("; ".join(problematic[:2]))  # Максимум 2 проблемы
    
    return ", ".join(comments)


def analyze_technical_issues(frame_data: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Анализирует технические проблемы во всех кадрах
    
    Возвращает словарь с частотой проблем
    """
    issues = {
        'elbow_problems': 0,
        'shoulder_problems': 0,
        'hip_problems': 0,
        'knee_problems': 0,
        'balance_problems': 0,
        'quality_problems': 0
    }
    
    for frame in frame_data:
        if not frame.get('valid'):
            continue
        
        # Проблемы с качеством
        if frame['pose_quality'] < 70:
            issues['quality_problems'] += 1
        
        # Проблемы с балансом
        if frame['balance_score'] < 50:
            issues['balance_problems'] += 1
        
        # Проблемы с углами
        angles = frame.get('angles', {})
        
        for joint, angle in angles.items():
            if angle < 60 or angle > 150:
                if 'elbow' in joint:
                    issues['elbow_problems'] += 1
                elif 'shoulder' in joint:
                    issues['shoulder_problems'] += 1
                elif 'hip' in joint:
                    issues['hip_problems'] += 1
                elif 'knee' in joint:
                    issues['knee_problems'] += 1
    
    return issues


