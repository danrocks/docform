from pydantic import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()