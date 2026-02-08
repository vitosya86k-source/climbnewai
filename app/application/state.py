"""Внутреннее состояние MVP (без БД)."""

import time
from typing import Dict, Any, Optional


class InMemoryAnalysisStore:
    """Хранит последний результат анализа по chat_id."""

    def __init__(self, max_items: int = 500, ttl_sec: int = 60 * 60):
        self._items: Dict[int, Dict[str, Any]] = {}
        self._max_items = max_items
        self._ttl_sec = ttl_sec

    def set(self, chat_id: int, result: Dict[str, Any]) -> None:
        now = time.time()
        self._items[chat_id] = {"result": result, "ts": now}
        self._cleanup(now)

    def get(self, chat_id: int) -> Optional[Dict[str, Any]]:
        item = self._items.get(chat_id)
        if not item:
            return None
        if time.time() - item["ts"] > self._ttl_sec:
            self._items.pop(chat_id, None)
            return None
        return item["result"]

    def _cleanup(self, now: float) -> None:
        # TTL cleanup
        expired = [k for k, v in self._items.items() if now - v["ts"] > self._ttl_sec]
        for k in expired:
            self._items.pop(k, None)

        # Size cleanup (remove oldest)
        if len(self._items) <= self._max_items:
            return
        sorted_items = sorted(self._items.items(), key=lambda kv: kv[1]["ts"])
        to_remove = len(self._items) - self._max_items
        for i in range(to_remove):
            self._items.pop(sorted_items[i][0], None)


analysis_store = InMemoryAnalysisStore()
