"""
cache.py — Cache layer com SQLite para evitar rate-limiting de APIs.
Serializa DataFrames e dicts com pickle, TTL configurável por tipo de dado.
"""
import sqlite3
import pickle
import time
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "cache.db"

# TTL padrão em horas por categoria
TTL_HOURS = {
    "macro": 24,
    "prices": 6,
    "fundamentals": 72,
    "sector": 48,
    "score": 12,
}


class DataCache:
    """SQLite-backed cache with TTL support."""

    def __init__(self, db_path=None):
        self.db_path = str(db_path or DB_PATH)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data BLOB NOT NULL,
                    category TEXT DEFAULT 'macro',
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()

    def get(self, key, category="macro"):
        """
        Retrieve cached data if not expired.
        Returns None if cache miss or expired.
        """
        ttl_sec = TTL_HOURS.get(category, 24) * 3600
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT data, created_at FROM cache WHERE key = ?",
                    (key,)
                ).fetchone()
            if row is None:
                return None
            blob, created = row
            if (time.time() - created) > ttl_sec:
                logger.debug(f"Cache expired for key={key}")
                return None
            return pickle.loads(blob)
        except Exception as e:
            logger.warning(f"Cache read error for key={key}: {e}")
            return None

    def set(self, key, data, category="macro"):
        """Store data in cache."""
        try:
            blob = pickle.dumps(data)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, data, category, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (key, blob, category, time.time())
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Cache write error for key={key}: {e}")

    def clear(self, category=None):
        """Clear all cache or a specific category."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if category:
                    conn.execute("DELETE FROM cache WHERE category = ?", (category,))
                else:
                    conn.execute("DELETE FROM cache")
                conn.commit()
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")

    def get_age_hours(self, key):
        """Return age of cache entry in hours, or None if not found."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT created_at FROM cache WHERE key = ?", (key,)
                ).fetchone()
            if row:
                return (time.time() - row[0]) / 3600
        except Exception:
            pass
        return None


# Singleton instance
_cache = None

def get_cache():
    global _cache
    if _cache is None:
        _cache = DataCache()
    return _cache
