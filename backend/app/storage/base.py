from typing import Protocol


class Storage(Protocol):
    """Everything outside this package talks to Storage, never to a specific backend.
    Swapping local disk for R2 in production is: change STORAGE_BACKEND, supply R2 creds.
    """

    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...

    def url_for(self, key: str) -> str: ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> None: ...
