"""Модуль сравнения с базой спортсменов"""

from .athlete_database import ATHLETE_DATABASE
from .comparator import find_similar_athletes, format_comparison

__all__ = ["ATHLETE_DATABASE", "find_similar_athletes", "format_comparison"]


