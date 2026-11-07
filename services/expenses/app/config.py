"""Service configuration, read only from environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str
    database_url: str
    api_key: str
    cors_origin: str


def get_settings() -> Settings:
    return Settings(
        service_name=os.getenv("SERVICE_NAME", "expenses"),
        database_url=os.getenv("DATABASE_URL", ""),
        # Empty API_KEY disables the check (local development only).
        api_key=os.getenv("API_KEY", ""),
        cors_origin=os.getenv("CORS_ORIGIN", "http://localhost:8080"),
    )
