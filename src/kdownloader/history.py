"""Historial de descargas terminadas (JSON, últimas 500)."""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .util import read_json, write_json_atomic

MAX_ITEMS = 500


@dataclass
class HistoryItem:
    id: str
    url: str
    title: str
    uploader: str
    thumbnail: str | None
    site: str
    option: str
    container: str
    file_path: str
    size: int
    finished_at: float

    def view(self) -> dict[str, Any]:
        d = asdict(self)
        path = Path(self.file_path) if self.file_path else None
        d.pop("file_path")
        if not str(self.url).startswith(("https://", "http://")):
            d["url"] = None
        d["file_name"] = path.name if path else None
        d["file_exists"] = bool(path and path.exists())
        return d


class History:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        raw = read_json(path, default=[]) or []
        self._items: list[HistoryItem] = []
        for entry in raw if isinstance(raw, list) else []:
            try:
                self._items.append(HistoryItem(**entry))
            except TypeError:
                continue

    def add(self, item: HistoryItem) -> None:
        with self._lock:
            self._items = [i for i in self._items if i.id != item.id]
            self._items.insert(0, item)
            del self._items[MAX_ITEMS:]
            self._save()

    def get(self, item_id: str) -> HistoryItem | None:
        with self._lock:
            return next((i for i in self._items if i.id == item_id), None)

    def list(self, query: str = "") -> list[dict[str, Any]]:
        q = (query or "").strip().lower()
        with self._lock:
            items = [i for i in self._items if not q or q in i.title.lower() or q in i.uploader.lower()]
            return [i.view() for i in items]

    def remove(self, item_id: str) -> None:
        with self._lock:
            self._items = [i for i in self._items if i.id != item_id]
            self._save()

    def clear(self) -> None:
        with self._lock:
            self._items = []
            self._save()

    def count(self) -> int:
        with self._lock:
            return len(self._items)

    def _save(self) -> None:
        write_json_atomic(self.path, [asdict(i) for i in self._items])


def now() -> float:
    return time.time()
