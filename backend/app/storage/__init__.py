from functools import lru_cache

from app.core.config import get_settings
from app.storage.base import Storage


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    if settings.storage_backend == "r2":
        from app.storage.r2 import R2Storage

        return R2Storage(
            account_id=settings.r2_account_id,
            access_key_id=settings.r2_access_key_id,
            secret_access_key=settings.r2_secret_access_key,
            bucket=settings.r2_bucket,
            endpoint_url=settings.r2_endpoint_url,
        )

    from app.storage.local import LocalDiskStorage

    return LocalDiskStorage(root=settings.storage_local_path, public_base_url=settings.storage_public_base_url)


__all__ = ["Storage", "get_storage"]
