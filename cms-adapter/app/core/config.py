from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    RABBITMQ_URL: str = "amqp://swift:swift@rabbitmq:5672/"
    EXCHANGE_NAME: str = "swifttrack.events"

    class Config:
        env_file = ".env"


settings = Settings()
