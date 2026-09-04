import asyncio
import json
import logging
import aio_pika
from app.core.config import settings
from app.core.ws_manager import manager

logger = logging.getLogger(__name__)

QUEUE_BINDINGS = {
    "notification.ros.route_assigned.queue": "ros.route_assigned",
    "notification.wms.registered.queue": "wms.registered",
    "notification.route.driver_unavailable.queue": "route.driver_unavailable",
    "notification.order.delivered.queue": "order.delivered",
    "notification.order.failed.queue": "order.failed",
}


async def handle_message(message: aio_pika.IncomingMessage, routing_key: str):
    async with message.process():
        try:
            body = json.loads(message.body)
            event = {"event": routing_key, "data": body}
            logger.info(f"Notification service broadcasting event: {routing_key}")
            await manager.broadcast(event)
        except Exception as e:
            logger.error(f"Notification consumer error: {e}", exc_info=True)


async def start_consumer():
    await asyncio.sleep(8)
    logger.info("Notification service connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    exchange = await channel.declare_exchange(
        settings.EXCHANGE_NAME,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )

    for queue_name, routing_key in QUEUE_BINDINGS.items():
        queue = await channel.declare_queue(queue_name, durable=True)
        await queue.bind(exchange, routing_key=routing_key)
        await queue.consume(lambda msg, rk=routing_key: handle_message(msg, rk))
        logger.info(f"Subscribed: {queue_name} → {routing_key}")

    logger.info("Notification consumer ready.")
    await asyncio.Future()
