from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    OPENAI_API_KEY: str
    GEMINI_KEY: str
    DEVIN_KEY: str
    ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    STORAGE_BACKEND: str = "db"
    DATABASE_URL: str = "postgresql://docform:docform@localhost:5432/docform"
    # DATABASE_URL: str = "postgresql://some-postgres:mysecretpassword@db:5432/postgres"

settings = Settings()