"""
ClimbAI — Алгоритм определения уровня лазания (v2)
====================================================
Замена старого estimate_grade() в swot_generator.py

Основные изменения:
- Расширенная шкала до 8b (потолок скалодромов РФ)
- Сниженные пороги для компенсации шума MediaPipe
- Пересбалансированные веса метрик
- Бонус за сложность движений
- Расчёт по всему видео, а не по последним 3 секундам
"""

from typing import Tuple, Optional, Dict, List
import statistics


# ============================================================
# 1. КОНФИГУРАЦИЯ
# ============================================================

# Веса техники (сумма = 1.0)
TECHNIQUE_WEIGHTS: Dict[str, float] = {
    'quiet_feet':      0.15,   # было 0.20 — MediaPipe шумит на лодыжках
    'hip_position':    0.15,   # было 0.20 — артефакты при съёмке сбоку
    'diagonal':        0.15,   # диагональная координация — стабильная метрика
    'grip_release':    0.15,   # плавность перехватов
    'rhythm':          0.15,   # было 0.10 — ритм хорошо отличает уровни
    'dynamic_control': 0.15,   # было 0.10 — динамика = индикатор уровня
    'route_reading':   0.10,   # считывание маршрута
}

# Компенсация систематического занижения MediaPipe (8-12 пунктов)
NOISE_COMPENSATION: float = 8.0

# Таблица порогов: (мин_скор, категория)
# Шаг ~3-4 пункта в верхней части (тонкие различия), ~5-7 в нижней
GRADE_TABLE: List[Tuple[float, str]] = [
    (95, "8b"),
    (92, "8a+—8b"),
    (89, "8a+"),
    (86, "8a"),
    (83, "7c+—8a"),
    (80, "7c+"),
    (77, "7c"),
    (74, "7b+—7c"),
    (70, "7b+"),
    (66, "7a—7b"),
    (62, "6c—7a"),
    (57, "6b—6c"),
    (51, "6a—6b"),
    (44, "5c—6a"),
    (37, "5b—5c"),
    (28, "5a—5b"),
    (0,  "до 5a"),
]

# Максимальная длина истории метрик (кадры)
# 3600 кадров = 2 мин при 30fps — покрывает любой боулдер
# None = без ограничения, берём всё видео
MAX_METRICS_HISTORY: int = None


# ============================================================
# 2. ОСНОВНАЯ ФУНКЦИЯ ОПРЕДЕЛЕНИЯ УРОВНЯ
# ============================================================

def estimate_grade(
    technique_metrics: Dict[str, float],
    video_stats: Optional[Dict] = None
) -> Tuple[str, float]:
    """
    Определяет категорию трассы по метрикам техники + доп. данным.

    Args:
        technique_metrics: dict с 7 метриками (0–100):
            - quiet_feet
            - hip_position
            - diagonal
            - grip_release
            - rhythm
            - dynamic_control
            - route_reading

        video_stats: опционально — доп. данные по видео:
            - total_frames (int): общее кол-во кадров
            - fps (float): частота кадров (по умолч. 30)
            - hand_moves_count (int): кол-во перехватов
            - dynamic_moves_count (int): кол-во динамических движений
            - max_reach_ratio (float): макс. разлёт рук / рост

    Returns:
        (grade_str, weighted_score) — категория и числовой скор
    """

    # --- 2a. Взвешенная сумма метрик ---
    weighted_score = sum(
        technique_metrics.get(key, 50) * weight
        for key, weight in TECHNIQUE_WEIGHTS.items()
    )

    # --- 2b. Компенсация шума MediaPipe ---
    weighted_score += NOISE_COMPENSATION

    # --- 2c. Бонус за сложность движений ---
    complexity_bonus = _calc_complexity_bonus(video_stats)
    weighted_score += complexity_bonus

    # --- 2d. Ограничение диапазона ---
    weighted_score = max(0.0, min(100.0, weighted_score))

    # --- 2e. Определение категории ---
    grade = _score_to_grade(weighted_score)

    return grade, round(weighted_score, 1)


# ============================================================
# 3. БОНУС ЗА СЛОЖНОСТЬ
# ============================================================

def _calc_complexity_bonus(video_stats: Optional[Dict]) -> float:
    """
    Начисляет бонусные баллы за признаки сложного лазания.
    Максимум ~8 баллов суммарно.
    """
    if not video_stats:
        return 0.0

    bonus = 0.0

    # --- Плотность перехватов (перехватов в секунду) ---
    moves = video_stats.get('hand_moves_count', 0)
    total_frames = video_stats.get('total_frames', 1)
    fps = video_stats.get('fps', 30)
    duration_sec = max(total_frames / fps, 0.1)
    move_density = moves / duration_sec

    if move_density > 1.8:
        bonus += 5.0   # очень быстрое лазание
    elif move_density > 1.2:
        bonus += 3.0   # быстрое лазание

    # --- Динамические движения ---
    dynamic = video_stats.get('dynamic_moves_count', 0)
    if dynamic >= 3:
        bonus += 4.0   # серьёзная динамика
    elif dynamic >= 1:
        bonus += 2.0   # есть элементы динамики

    # --- Большой разлёт рук (сложные растяжки) ---
    reach = video_stats.get('max_reach_ratio', 0)
    if reach > 0.7:
        bonus += 2.0

    # Ограничиваем суммарный бонус
    return min(bonus, 8.0)


# ============================================================
# 4. ПЕРЕВОД СКОРА В КАТЕГОРИЮ
# ============================================================

def _score_to_grade(score: float) -> str:
    """Находит категорию по таблице порогов."""
    for threshold, grade in GRADE_TABLE:
        if score >= threshold:
            return grade
    return "до 5a"


# ============================================================
# 5. АГРЕГАЦИЯ МЕТРИК ПО ВСЕМУ ВИДЕО
# ============================================================

def aggregate_metrics_history(
    metrics_history: List[Dict[str, float]]
) -> Dict[str, float]:
    """
    Считает средние метрики по ВСЕЙ истории кадров, а не по последним 90.

    Args:
        metrics_history: список dict'ов с метриками по каждому кадру

    Returns:
        dict со средними значениями каждой метрики
    """
    if not metrics_history:
        return {key: 50.0 for key in TECHNIQUE_WEIGHTS}

    # Берём всё видео целиком
    history = metrics_history if MAX_METRICS_HISTORY is None else metrics_history[-MAX_METRICS_HISTORY:]

    aggregated = {}
    for key in TECHNIQUE_WEIGHTS:
        values = [frame.get(key, 50.0) for frame in history if key in frame]
        if values:
            # Используем медиану — устойчивее к выбросам от MediaPipe
            aggregated[key] = statistics.median(values)
        else:
            aggregated[key] = 50.0

    return aggregated


# ============================================================
# 6. ИСПРАВЛЕННЫЕ ПОРОГИ ОТДЕЛЬНЫХ МЕТРИК
# ============================================================

def calc_quiet_feet_score(avg_readjustments: float) -> float:
    """
    Оценка точности постановки ног.
    Смягчённые пороги: MediaPipe даёт ложные перестановки из-за дрожания.

    Args:
        avg_readjustments: среднее кол-во перестановок на одной точке опоры
    """
    if avg_readjustments < 2.0:
        score = 90 + (2.0 - avg_readjustments) / 2.0 * 10
    elif avg_readjustments < 3.5:
        score = 70 + (3.5 - avg_readjustments) / 1.5 * 20
    elif avg_readjustments < 5.0:
        score = 50 + (5.0 - avg_readjustments) / 1.5 * 20
    else:
        score = max(20, 50 - (avg_readjustments - 5.0) * 10)
    return round(max(20, min(100, score)), 1)


def calc_hip_position_score(angle_deg: float) -> float:
    """
    Оценка положения таза.
    Смягчённые пороги: камера сбоку/снизу искажает угол.

    Args:
        angle_deg: угол между линией таз-плечи и вертикалью (градусы)
    """
    if angle_deg < 15:
        score = 90 + (15 - angle_deg) / 15 * 10
    elif angle_deg < 25:
        score = 70 + (25 - angle_deg) / 10 * 20
    elif angle_deg < 40:
        score = 50 + (40 - angle_deg) / 15 * 20
    else:
        score = max(20, 50 - (angle_deg - 40) * 1.5)
    return round(max(20, min(100, score)), 1)


def calc_diagonal_score(correlation: float, is_static: bool = False) -> float:
    """
    Оценка диагональной координации.
    Без изменений — метрика стабильна.

    Args:
        correlation: корреляция Пирсона (диагональные пары)
        is_static: True если скалолаз почти не двигается
    """
    if is_static:
        return 60.0

    if correlation > 0.8:
        score = 90 + (correlation - 0.8) / 0.2 * 10
    elif correlation > 0.6:
        score = 70 + (correlation - 0.6) / 0.2 * 20
    elif correlation > 0.4:
        score = 50 + (correlation - 0.4) / 0.2 * 20
    elif correlation > 0.1:
        score = 30 + (correlation - 0.1) / 0.3 * 20
    else:
        score = 10
    return round(max(10, min(100, score)), 1)


def calc_rhythm_score(interval_std_ms: float) -> float:
    """
    Оценка ритма лазания.
    Смягчено: std ≤150ms (было 100) = отличный ритм.

    Args:
        interval_std_ms: стд. отклонение интервалов между перехватами (мс)
    """
    if interval_std_ms <= 150:
        score = 90 + (150 - interval_std_ms) / 150 * 10
    elif interval_std_ms <= 250:
        score = 70 + (250 - interval_std_ms) / 100 * 20
    elif interval_std_ms <= 400:
        score = 50 + (400 - interval_std_ms) / 150 * 20
    else:
        score = max(20, 50 - (interval_std_ms - 400) * 0.05)
    return round(max(20, min(100, score)), 1)


def calc_grip_release_score(jerk_count: int) -> float:
    """
    Оценка плавности перехватов.
    Смягчено: штраф 15 за рывок (было 20).

    Args:
        jerk_count: кол-во резких ускорений (accel > 0.01)
    """
    score = 100 - jerk_count * 15
    return round(max(15, min(100, score)), 1)


def calc_dynamic_control_score(
    has_dynamic: bool,
    stabilization_score: float = 100.0,
    landing_deviation: float = 0.0
) -> float:
    """
    Оценка контроля динамических движений.

    Args:
        has_dynamic: были ли динамические движения
        stabilization_score: оценка стабилизации после динамики (0-100)
        landing_deviation: отклонение точки приземления
    """
    if not has_dynamic:
        return 80.0  # было 100 — нет динамики ≠ идеальный контроль

    score = stabilization_score - landing_deviation * 200
    return round(max(15, min(100, score)), 1)


def calc_route_reading_score(
    time_to_first_move_sec: float,
    pause_count: int
) -> float:
    """
    Оценка считывания маршрута.
    Без изменений — логика адекватна.

    Args:
        time_to_first_move_sec: время до первого перехвата (сек)
        pause_count: кол-во пауз 1-3 сек между движениями
    """
    # Оценка старта (макс 50)
    if time_to_first_move_sec <= 5:
        start_score = 50
    elif time_to_first_move_sec <= 10:
        start_score = 30
    else:
        start_score = 15

    # Оценка пауз (макс 50) — паузы = обдумывание = хорошо
    if pause_count >= 3:
        pause_score = 50
    elif pause_count >= 1:
        pause_score = 30
    else:
        pause_score = 15

    score = start_score + pause_score
    return round(max(20, min(100, score)), 1)


# ============================================================
# 7. СБОР VIDEO_STATS (хелпер для интеграции)
# ============================================================

def collect_video_stats(overlays) -> Dict:
    """
    Собирает video_stats из объекта overlays для передачи в estimate_grade.
    Адаптируй под свою структуру данных.

    Args:
        overlays: объект с данными анализа видео

    Returns:
        dict с video_stats
    """
    stats = {
        'total_frames': getattr(overlays, 'total_frames', 0),
        'fps': getattr(overlays, 'fps', 30),
        'hand_moves_count': getattr(overlays, 'hand_moves_count', 0),
        'dynamic_moves_count': getattr(overlays, 'dynamic_moves_count', 0),
        'max_reach_ratio': getattr(overlays, 'max_reach_ratio', 0.0),
    }
    return stats


# ============================================================
# 8. ТОЧКА ИНТЕГРАЦИИ — замена в swot_generator.py
# ============================================================

def get_climbing_grade(overlays) -> Tuple[str, float]:
    """
    Drop-in замена для вызова из swot_generator.py.

    Вместо:
        avg_metrics = mean(overlays.technique_metrics_history[-90:])
        grade = old_estimate_grade(avg_metrics)

    Используй:
        from grade_algorithm import get_climbing_grade
        grade, score = get_climbing_grade(overlays)
    """
    # Агрегируем по всему видео (не 90 кадров!)
    avg_metrics = aggregate_metrics_history(
        overlays.technique_metrics_history
    )

    # Собираем доп. статистику
    video_stats = collect_video_stats(overlays)

    # Определяем уровень
    grade, score = estimate_grade(avg_metrics, video_stats)

    return grade, score


# ============================================================
# DEBUG / ТЕСТИРОВАНИЕ
# ============================================================

if __name__ == "__main__":
    # Пример: средний скалолаз ~6b
    test_metrics = {
        'quiet_feet': 65,
        'hip_position': 60,
        'diagonal': 55,
        'grip_release': 70,
        'rhythm': 60,
        'dynamic_control': 80,
        'route_reading': 50,
    }

    grade, score = estimate_grade(test_metrics)
    print(f"Без video_stats:  {grade} (скор: {score})")

    # Тот же скалолаз, но с быстрой динамикой
    test_stats = {
        'total_frames': 450,
        'fps': 30,
        'hand_moves_count': 25,
        'dynamic_moves_count': 2,
        'max_reach_ratio': 0.65,
    }

    grade, score = estimate_grade(test_metrics, test_stats)
    print(f"С video_stats:    {grade} (скор: {score})")

    # Тест всех уровней
    print("\n--- Таблица уровней ---")
    for s in range(0, 101, 5):
        g = _score_to_grade(s)
        print(f"  Скор {s:3d} → {g}")
