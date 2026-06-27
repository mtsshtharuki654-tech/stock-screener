from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    jquants_api_key: str = ""
    cache_dir: Path = Path("./data")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def model_post_init(self, __context):
        self.cache_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
