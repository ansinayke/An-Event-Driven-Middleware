import json
import logging
import aio_pika
from app.core.config import settings

logger = logging.getLogger(__name__)

_connection = None
_channel = None
_exchange = None


async def get_exchange():
    global _connection, _channel, _exchange
    if _exchange is None:
        _connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        _channel = await _connection.channel()
        _exchange = await _channel.declare_exchange(
            settings.EXCHANGE_NAME,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
    return _exchange


async def publish_event(routing_key: str, body: dict):
    exchange = await get_exchange()
    message = aio_pika.Message(
        body=json.dumps(body).encode(),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        content_type="application/json",
    )
    await exchange.publish(message, routing_key=routing_key)
    logger.info(f"Published event: {routing_key} | {body}")


async def close_publisher():
    global _connection
    if _connection:
        await _connection.close()
