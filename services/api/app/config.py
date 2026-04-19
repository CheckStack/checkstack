from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/checkstack"
    check_interval_seconds: int = 15
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    public_base_url: str = "http://localhost:3000"

    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "checkstack@localhost"
    smtp_use_tls: bool = True

    slack_default_webhook_url: str = ""


settings = Settings()
