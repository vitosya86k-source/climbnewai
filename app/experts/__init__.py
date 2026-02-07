"""Модуль экспертных оценок"""

from .expert_selector import select_expert
from .expert_profiles import EXPERTS

__all__ = ["select_expert", "EXPERTS"]


