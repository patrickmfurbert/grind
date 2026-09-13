from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str = ""
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    ollama_host: str = "http://localhost:11434"
    sqlite_db_path: str = "./grind.db"
    pdf_upload_dir: str = "./uploads"
    code_execution_timeout: int = 10

    @property
    def upload_path(self) -> Path:
        return Path(self.pdf_upload_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
