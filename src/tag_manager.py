"""
Persistent JSON-backed storage for tag mappings and application settings.

The database file is human-editable (pretty-printed JSON). Writes are
atomic: data is written to a temporary file first, then renamed into
place, so a crash mid-write cannot corrupt the database.
"""

import json
import logging
import os
import tempfile
from typing import Any

from config import DB_PATH

logger = logging.getLogger(__name__)

_DEFAULT_DB: dict = {
    "tags": {},
    "settings": {
        "speakers": {
            "coordinator": None,
            "join": []
        }
    }
}


class TagManager:
    """Read and write tag configuration and application settings."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self._data: dict = {}
        self._load()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load the database from disk, creating it if absent."""
        if not os.path.exists(self.db_path):
            self._data = _DEFAULT_DB.copy()
            self._save()
            return

        try:
            with open(self.db_path, 'r', encoding='utf-8') as fh:
                self._data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load %s (%s). Starting with empty DB.", self.db_path, exc)
            self._data = _DEFAULT_DB.copy()

    def _save(self) -> None:
        """Atomically write the database to disk."""
        dir_name = os.path.dirname(self.db_path) or '.'
        try:
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                json.dump(self._data, fh, indent=4, ensure_ascii=False)
            os.replace(tmp_path, self.db_path)
        except OSError as exc:
            logger.error("Failed to save database: %s", exc)

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------

    def get_tag(self, uid: str) -> dict | None:
        """Return the config dict for *uid*, or ``None``."""
        self._load()
        return self._data.get('tags', {}).get(uid)

    def set_tag(self, uid: str, data: dict) -> None:
        """Create or overwrite the tag entry for *uid*."""
        self._load()
        self._data.setdefault('tags', {})[uid] = data
        self._save()

    def get_all_tags(self) -> dict:
        """Return ``{uid: config, ...}`` for every registered tag."""
        self._load()
        return self._data.get('tags', {})

    def delete_tag(self, uid: str) -> bool:
        """Delete tag *uid*. Returns ``True`` if it existed."""
        self._load()
        tags = self._data.get('tags', {})
        if uid in tags:
            del tags[uid]
            self._save()
            return True
        return False

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Return a single top-level setting value."""
        self._load()
        return self._data.get('settings', {}).get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        """Write a single top-level setting value."""
        self._load()
        self._data.setdefault('settings', {})[key] = value
        self._save()
