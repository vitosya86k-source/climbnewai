"""
BoulderVision модуль для ClimbAI

Интеграция алгоритмов из:
- https://github.com/reiffd7/BoulderVision

Возможности:
- Velocity Ratio (коэффициент скорости)
- Cumulative Distance (накопленная дистанция)
- Keypoints History (буфер кадров для анализа паттернов)
- Heatmaps (тепловые карты)
- Movement Trajectories (траектории движения)
"""

from .metrics import (
    BoulderVisionMetrics, 
    compute_trajectory_similarities,
    compute_trajectory_efficiency,
    compute_straight_arms_efficiency,
    format_movement_analysis
)
__all__ = [
    'BoulderVisionMetrics',
    'compute_trajectory_similarities',
    'compute_trajectory_efficiency',
    'compute_straight_arms_efficiency',
    'format_movement_analysis'
]
