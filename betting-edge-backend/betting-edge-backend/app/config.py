from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    odds_api_key: str
    frontend_origins: str = "http://localhost:5173,http://localhost:3000"
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    default_region: str = "us"
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def allowed_origins(self):
        return [x.strip() for x in self.frontend_origins.split(",") if x.strip()]

@lru_cache
def get_settings():
    return Settings()
