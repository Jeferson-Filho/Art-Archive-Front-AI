"""
Application configuration, read exclusively from environment variables.

Implements doc 99 (Decisions 2, 4, 5) and RNF-005 (doc 02.5): no credential
is ever hardcoded in source.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Harvard Art Museums API (doc 04 §4 — Harvard Proxy module)
    harvard_api_key: str = ""
    harvard_api_base_url: str = "https://api.harvardartmuseums.org"

    # CORS — origin of the Next.js front-end (doc 07 §1)
    frontend_origin: str = "http://localhost:3000"

    # Generation timeout budget (RNF-002), used from Phase 4 onward
    generation_timeout_seconds: int = 60

    # Database connection (used from Phase 2 onward)
    database_url: str = ""

    # Azure OpenAI (doc 09, §6; doc 99, Decision 9). The endpoint is the
    # resource URL; the deployment name is what the API addresses, not the model
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
