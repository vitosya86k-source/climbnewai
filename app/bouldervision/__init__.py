"""
BoulderVision модуль для ClimbAI

Интеграция алгоритмов из:
- https://github.com/reiffd7/BoulderVision
- https://blog.roboflow.com/bouldering/

Возможности:
- Velocity Ratio (коэффициент скорости)
- Cumulative Distance (накопленная дистанция)
- Keypoints History (буфер кадров для анализа паттернов)
- Hold Detection (детекция зацепов через Roboflow)
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
from .holds_detector import HoldsDetector

__all__ = [
    'BoulderVisionMetrics',
    'compute_trajectory_similarities',
    'compute_trajectory_efficiency',
    'compute_straight_arms_efficiency',
    'format_movement_analysis',
    'HoldsDetector'
]
