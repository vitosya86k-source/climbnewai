"""
PATCH: Rotation Filter для Quiet Feet
Файл: app/analysis/technique_metrics.py

Суть: отличаем пивот (поворот стопы на месте) от реальной перестановки.
Если центр стопы остался в том же кластере, но угол изменился — это пивот, не перестановка.

Вставить в класс TechniqueMetricsAnalyzer.
"""


# ============================================================
# 1. Новый метод: определение угла стопы
# ============================================================
# Добавить в класс TechniqueMetricsAnalyzer

def _calc_foot_angle(self, landmarks, foot_side: str) -> float:
    """
    Угол стопы относительно горизонтали.
    Считаем по вектору пятка → носок.
    
    foot_side: 'left' или 'right'
    Возвращает: угол в градусах (0-360)
    """
    import math
    
    if foot_side == 'left':
        heel_idx = 29   # LEFT_HEEL (MediaPipe Pose)
        toe_idx = 31     # LEFT_FOOT_INDEX
    else:
        heel_idx = 30   # RIGHT_HEEL
        toe_idx = 32     # RIGHT_FOOT_INDEX
    
    heel = landmarks[heel_idx]
    toe = landmarks[toe_idx]
    
    dx = toe.x - heel.x
    dy = toe.y - heel.y
    
    angle = math.degrees(math.atan2(dy, dx))
    return angle % 360


# ============================================================
# 2. Модифицированный подсчёт перестановок
# ============================================================
# Заменить текущую логику подсчёта repositions в _analyze_quiet_feet

# --- БЫЛО (примерная логика из описания) ---
"""
for position in foot_positions:
    cluster = find_cluster(position, clusters, threshold=0.02)
    if cluster is not None:
        cluster.add(position)
        repositions += 1  # <-- каждое попадание в существующий кластер = перестановка
    else:
        clusters.append(new_cluster(position))
"""

# --- СТАЛО ---

# Константы (добавить к существующим в начале класса)
ROTATION_THRESHOLD_DEG = 15.0  # минимальный поворот стопы для "пивота"
POSITION_THRESHOLD = 0.02      # существующий порог кластеризации (не меняем)


def _is_pivot(self, prev_angle: float, curr_angle: float) -> bool:
    """
    Определяет, является ли движение пивотом (поворотом стопы на месте).
    
    Пивот = центр стопы остался в кластере, но угол изменился >= ROTATION_THRESHOLD_DEG.
    Если угол почти не изменился — это реальная перестановка (ёрзанье).
    Если угол изменился значительно — это пивот (техника).
    """
    angle_diff = abs(curr_angle - prev_angle)
    # Нормализация: угол может перескочить через 360
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    
    return angle_diff >= self.ROTATION_THRESHOLD_DEG


def _count_repositions_with_rotation_filter(
    self, 
    foot_positions: list,
    foot_angles: list,
    threshold: float = 0.02
) -> tuple:
    """
    Подсчёт перестановок с фильтром пивотов.
    
    Args:
        foot_positions: список (x, y) центров стопы по кадрам
        foot_angles: список углов стопы по кадрам (из _calc_foot_angle)
        threshold: порог кластеризации (нормализованные координаты)
    
    Returns:
        (total_repositions, total_pivots, total_stable_positions)
        
    Логика:
        - Если стопа попала в существующий кластер И угол изменился >= 15° → пивот (НЕ считаем)
        - Если стопа попала в существующий кластер И угол НЕ изменился → перестановка (считаем)
        - Если стопа в новом месте → новый кластер (не считаем)
    """
    clusters = []  # list of {'center': (x,y), 'last_angle': float, 'count': int}
    total_repositions = 0
    total_pivots = 0
    total_stable = 0
    
    for i, (pos, angle) in enumerate(zip(foot_positions, foot_angles)):
        matched_cluster = None
        
        # Ищем ближайший кластер
        for cluster in clusters:
            dist = ((pos[0] - cluster['center'][0])**2 + 
                    (pos[1] - cluster['center'][1])**2) ** 0.5
            if dist < threshold:
                matched_cluster = cluster
                break
        
        if matched_cluster is not None:
            # Стопа в том же месте — пивот или перестановка?
            if self._is_pivot(matched_cluster['last_angle'], angle):
                total_pivots += 1
                # Пивот — обновляем угол, НЕ считаем как перестановку
            else:
                total_repositions += 1
                # Реальная перестановка — ёрзанье на месте
            
            # Обновляем состояние кластера
            matched_cluster['last_angle'] = angle
            matched_cluster['count'] += 1
        else:
            # Новая точка опоры
            clusters.append({
                'center': pos,
                'last_angle': angle,
                'count': 1
            })
            total_stable += 1
    
    return total_repositions, total_pivots, total_stable


# ============================================================
# 3. Интеграция в analyze_frame / финальный расчёт
# ============================================================

def _calculate_quiet_feet_score(self, total_repositions, total_stable):
    """
    Без изменений — та же формула, но на входе уже отфильтрованные данные.
    total_repositions теперь НЕ включает пивоты.
    """
    if total_stable == 0:
        return 75.0  # fallback
    
    avg_repositions = total_repositions / total_stable
    
    if avg_repositions < 1.5:
        score = 90 + (1.5 - avg_repositions) * 6.67
    elif avg_repositions < 2.5:
        score = 70 + (2.5 - avg_repositions) * 19
    elif avg_repositions < 4.0:
        score = 50 + (4.0 - avg_repositions) * 13.33
    else:
        score = 50 - (avg_repositions - 4.0) * 12.5
    
    return max(20, min(100, score))


# ============================================================
# 4. Что нужно изменить в analyze_frame()
# ============================================================
"""
В методе analyze_frame() для каждого кадра:

БЫЛО:
    foot_pos = self._get_foot_center(landmarks, side)
    self.foot_history[side].append(foot_pos)

СТАЛО:
    foot_pos = self._get_foot_center(landmarks, side)
    foot_angle = self._calc_foot_angle(landmarks, side)
    self.foot_history[side].append(foot_pos)
    self.foot_angle_history[side].append(foot_angle)  # <- новый буфер

И в __init__ добавить:
    self.foot_angle_history = {'left': [], 'right': []}

В финальном расчёте (после прохода видео):

БЫЛО:
    repositions = self._count_repositions(self.foot_history[side])

СТАЛО:
    repositions, pivots, stable = self._count_repositions_with_rotation_filter(
        self.foot_history[side],
        self.foot_angle_history[side]
    )
    # repositions уже без пивотов
"""


# ============================================================
# 5. Дополнительно: логирование для отладки
# ============================================================

def _log_quiet_feet_debug(self, side, repositions, pivots, stable):
    """
    Для отладки — чтобы видеть сколько пивотов отфильтровали.
    Можно убрать после калибровки.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    total_events = repositions + pivots
    if total_events > 0:
        pivot_pct = (pivots / total_events) * 100
    else:
        pivot_pct = 0
    
    logger.info(
        f"QuietFeet [{side}]: "
        f"repositions={repositions}, pivots={pivots} ({pivot_pct:.0f}% filtered), "
        f"stable_positions={stable}, "
        f"avg_repositions={repositions/max(stable,1):.2f}"
    )
