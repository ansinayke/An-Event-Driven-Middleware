from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@auth-db:5432/authdb"

    class Config:
        env_file = ".env"


settings = Settings()
