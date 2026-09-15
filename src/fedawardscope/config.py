"""Application settings with environment-variable overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration for local and deployed environments."""

    database_path: Path = Path("data/fedawardscope.duckdb")
    api_base_url: str = "https://api.usaspending.gov"
    request_timeout_seconds: float = 30.0
    max_retries: int = 4

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_path=Path(
                os.getenv("FEDAWARDSCOPE_DATABASE_PATH", "data/fedawardscope.duckdb")
            ),
            api_base_url=os.getenv(
                "FEDAWARDSCOPE_API_BASE_URL", "https://api.usaspending.gov"
            ).rstrip("/"),
            request_timeout_seconds=float(
                os.getenv("FEDAWARDSCOPE_REQUEST_TIMEOUT_SECONDS", "30")
            ),
            max_retries=int(os.getenv("FEDAWARDSCOPE_MAX_RETRIES", "4")),
        )
