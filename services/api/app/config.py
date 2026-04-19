from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/checkstack"
    check_interval_seconds: int = 15
    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
