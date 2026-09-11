import json
from threading import Lock

from app.storage import Storage

CURRENT_POINTER_KEY = "catalog/current.json"


class CatalogCache:
    """The published catalogue, held in memory and refreshed only on publish (or process
    start). GET /catalog and /catalog/search are answered entirely from this — no DB query
    in the read hot path, per the brief. See README Part E for the honest answer on how far
    this scales before it needs to become Postgres FTS."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._catalog: dict | None = None

    def get(self) -> dict | None:
        with self._lock:
            return self._catalog

    def set(self, catalog: dict) -> None:
        with self._lock:
            self._catalog = catalog

    def refresh_from_storage(self, storage: Storage) -> None:
        try:
            pointer = json.loads(storage.get(CURRENT_POINTER_KEY))
            catalog = json.loads(storage.get(pointer["key"]))
        except FileNotFoundError:
            return  # nothing has ever been published yet
        self.set(catalog)


catalog_cache = CatalogCache()
