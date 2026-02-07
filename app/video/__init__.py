"""Модуль обработки видео"""

from .processor import VideoProcessor
from .ghost_manager import (
    GhostManager,
    ghost_manager,
    create_ghost_from_video,
    load_ghost_for_overlay,
    list_available_ghosts
)

__all__ = [
    "VideoProcessor",
    "GhostManager",
    "ghost_manager",
    "create_ghost_from_video",
    "load_ghost_for_overlay",
    "list_available_ghosts"
]


