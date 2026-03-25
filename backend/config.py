from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    OPENAI_API_KEY: str
    GEMINI_KEY: str
    ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

settings = Settings()