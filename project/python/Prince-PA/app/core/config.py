from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Prince-PA"
    deepseek_api_key: str = ""
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"

    @property
    def sqlite_url(self) -> str:
        return f"sqlite:///{self.data_dir / 'app.db'}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
