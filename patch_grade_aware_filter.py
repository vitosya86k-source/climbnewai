"""
PATCH: Grade-Aware фильтр для SWOT Generator
Файл: app/analysis/swot_generator.py

Суть: для скалолазов 7a+ поднимаем порог попадания quiet_feet в weaknesses.
Микродвижения на высоких категориях — часто техника, а не ошибка.
Также адаптируем тексты: не пишем "критично для прогресса" человеку на 7C.
"""


# ============================================================
# 1. Пороговая таблица по категориям
# ============================================================

# Стандартные пороги (текущие, без изменений)
DEFAULT_THRESHOLDS = {
    'strengths': 75,    # >= 75 попадает в сильные стороны
    'weaknesses': 55,   # < 55 попадает в слабые стороны
}

# Пороги для 7a+ (ужесточённые — сложнее попасть в weakness)
ADVANCED_THRESHOLDS = {
    'quiet_feet': {
        'weaknesses': 40,   # было 55, стало 40 — нужен реально низкий скор
        'strengths': 80,    # чуть выше планка для "сильной стороны"
    },
    'rhythm': {
        'weaknesses': 45,   # на 7a+ ритм может быть рваным из-за сложности
    },
    'route_reading': {
        'weaknesses': 40,   # опытные лезут "по памяти", меньше пауз — это норма
    },
    # Остальные метрики — без изменений
}

# С какого grade включается адаптация
ADVANCED_GRADE_THRESHOLD = '7a'

# Порядок категорий для сравнения
GRADE_ORDER = [
    'до 5a', '5a—5b', '5b—5c', '5c—6a', '6a—6b', '6b—6c',
    '6c—7a', '7a—7b', '7b+—7c', '7b+', '7c', '7c+',
    '7c+—8a', '8a', '8a+', '8a+—8b', '8b'
]


def _is_advanced_grade(estimated_grade: str) -> bool:
    """
    Определяет, является ли оценённая категория >= 7a.
    """
    if not estimated_grade:
        return False
    
    # Ищем позицию в таблице
    grade_lower = estimated_grade.strip().lower()
    
    # Индекс 7a—7b = 7 (первая категория >= 7a)
    advanced_start = None
    for i, g in enumerate(GRADE_ORDER):
        if '7a' in g.lower():
            advanced_start = i
            break
    
    if advanced_start is None:
        return False
    
    for i, g in enumerate(GRADE_ORDER):
        if g.lower() == grade_lower or grade_lower in g.lower():
            return i >= advanced_start
    
    # Fallback: если grade содержит 7, 8 — считаем advanced
    for ch in ['7', '8']:
        if ch in estimated_grade:
            return True
    
    return False


# ============================================================
# 2. Модифицированная функция определения weakness/strength
# ============================================================

def get_threshold(metric_name: str, block: str, estimated_grade: str) -> int:
    """
    Возвращает порог для метрики с учётом категории скалолаза.
    
    Args:
        metric_name: название метрики (quiet_feet, rhythm, etc.)
        block: 'weaknesses' или 'strengths'
        estimated_grade: оценённая категория ('7a—7b', '6b—6c', etc.)
    
    Returns:
        int: пороговое значение
    """
    # Проверяем, нужна ли адаптация
    if _is_advanced_grade(estimated_grade):
        # Есть ли специальный порог для этой метрики?
        if metric_name in ADVANCED_THRESHOLDS:
            if block in ADVANCED_THRESHOLDS[metric_name]:
                return ADVANCED_THRESHOLDS[metric_name][block]
    
    # Стандартный порог
    return DEFAULT_THRESHOLDS.get(block, 55)


# ============================================================
# 3. Интеграция в generate_swot()
# ============================================================
"""
В методе SWOTGenerator.generate_swot() заменить хардкод порогов:

БЫЛО:
    if score < 55:
        weaknesses.append(metric)
    elif score >= 75:
        strengths.append(metric)

СТАЛО:
    weakness_threshold = get_threshold(metric_name, 'weaknesses', estimated_grade)
    strength_threshold = get_threshold(metric_name, 'strengths', estimated_grade)
    
    if score < weakness_threshold:
        weaknesses.append(metric)
    elif score >= strength_threshold:
        strengths.append(metric)
"""


# ============================================================
# 4. Адаптация текстов для 7a+
# ============================================================

# Замена текстов quiet_feet для advanced уровней
ADVANCED_TEXT_OVERRIDES = {
    'quiet_feet': {
        'medium': {
            'weaknesses': (
                'Работа ног {score}% — есть пространство для повышения точности '
                'постановки. На вашем уровне это тонкая настройка.'
            ),
            'metric_info': (
                '{repositions} корректировки на зацепку. '
                'Для вашего уровня некритично, но точность ног — '
                'резерв для экономии энергии на длинных маршрутах.'
            ),
        },
        'poor': {
            # На 7a+ "poor" quiet_feet — скорее всего ложное срабатывание.
            # Но если rotation filter не помог и скор реально низкий:
            'weaknesses': (
                'Точность постановки ног {score}% — ниже ожидаемого для вашего уровня. '
                'Возможно, стоит обратить внимание на осознанность работы ног.'
            ),
        },
    },
    'rhythm': {
        'medium': {
            'weaknesses': (
                'Ритм {score}% — на сложных участках темп неравномерный. '
                'Это нормально для вашей категории, но ровный ритм '
                'поможет экономить на длинных трассах.'
            ),
        },
    },
}


def get_text_template(
    metric_name: str, 
    level: str, 
    block: str, 
    estimated_grade: str,
    default_text: str
) -> str:
    """
    Возвращает текст шаблона с учётом категории.
    Если есть override для advanced — использует его.
    Иначе — возвращает стандартный текст.
    """
    if _is_advanced_grade(estimated_grade):
        overrides = ADVANCED_TEXT_OVERRIDES.get(metric_name, {})
        level_overrides = overrides.get(level, {})
        if block in level_overrides:
            return level_overrides[block]
    
    return default_text


# ============================================================
# 5. Адаптация opportunity текстов
# ============================================================

ADVANCED_OPPORTUNITY_OVERRIDES = {
    'quiet_feet': (
        'Повышение точности постановки ног — тонкий резерв экономии. '
        'На вашем уровне это может дать преимущество на длинных и силовых маршрутах.'
    ),
}


def get_opportunity_text(metric_name: str, estimated_grade: str, default_text: str) -> str:
    """
    Для 7a+ заменяет opportunity тексты на более адекватные.
    """
    if _is_advanced_grade(estimated_grade):
        if metric_name in ADVANCED_OPPORTUNITY_OVERRIDES:
            return ADVANCED_OPPORTUNITY_OVERRIDES[metric_name]
    
    return default_text


# ============================================================
# 6. Полная интеграция: куда вставлять в generate_swot()
# ============================================================
"""
def generate_swot(self, metrics, analysis_data):
    estimated_grade = analysis_data.get('estimated_grade', '')
    
    strengths = []
    weaknesses = []
    opportunities = []
    threats = []
    
    for metric_name, score in metrics.items():
        # 1. Получаем порог с учётом grade
        w_threshold = get_threshold(metric_name, 'weaknesses', estimated_grade)
        s_threshold = get_threshold(metric_name, 'strengths', estimated_grade)
        
        # 2. Определяем уровень
        level = self._get_level(metric_name, score)
        
        # 3. Получаем текст с учётом grade
        if score < w_threshold:
            text = self._get_template(metric_name, level, 'weaknesses')
            text = get_text_template(metric_name, level, 'weaknesses', estimated_grade, text)
            weaknesses.append({'metric': metric_name, 'text': text, 'score': score})
            
            # Opportunity тоже адаптируем
            opp_text = self._get_opportunity(metric_name)
            opp_text = get_opportunity_text(metric_name, estimated_grade, opp_text)
            opportunities.append({'metric': metric_name, 'text': opp_text})
            
        elif score >= s_threshold:
            text = self._get_template(metric_name, level, 'strengths')
            strengths.append({'metric': metric_name, 'text': text, 'score': score})
    
    # ... threats logic без изменений ...
    
    return {
        'strengths': strengths[:4],
        'weaknesses': weaknesses[:4],
        'opportunities': opportunities[:3],
        'threats': threats[:3],
    }
"""
