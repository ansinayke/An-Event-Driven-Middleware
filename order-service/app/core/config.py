from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@order-db:5432/orderdb"
    JWT_SECRET: str = "DFGMD43"
    JWT_ALGORITHM: str = "HS256"
    RABBITMQ_URL: str = "amqp://swift:swift@rabbitmq:5672/"
    EXCHANGE_NAME: str = "swifttrack.events"

    class Config:
        env_file = ".env"


settings = Settings()
