import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "Martian Map API"
    app_version: str = "0.1.0"
    data_dir: Path = Path("data")
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )


@lru_cache
def get_settings() -> Settings:
    data_dir = Path(os.getenv("MARTIAN_MAP_DATA_DIR", "data")).expanduser().resolve()
    raw_origins = os.getenv(
        "MARTIAN_MAP_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    origins = tuple(item.strip() for item in raw_origins.split(",") if item.strip())
    return Settings(data_dir=data_dir, cors_origins=origins)
