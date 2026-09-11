from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "peblo-tv-mini"
    app_version: str = "0.1.0"
    environment: str = "development"

    database_url: str

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    storage_backend: str = "local"  # "local" | "r2"
    storage_local_path: str = "/data/storage"
    storage_public_base_url: str = "http://localhost:8000/storage"

    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""
    r2_endpoint_url: str = ""

    seed_editor_email: str = "editor@peblo.test"
    seed_editor_password: str = "editor12345"
    seed_admin_email: str = "admin@peblo.test"
    seed_admin_password: str = "admin12345"

    artwork_max_bytes: int = 200 * 1024
    artwork_aspect_tolerance: float = 0.01

    # Comma-separated list — the CMS and viewer are separate origins (different ports in
    # dev, likely different subdomains in prod), so the browser needs this to call the API.
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
