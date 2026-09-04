import asyncio
import json
import logging
import aio_pika
import httpx
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

QUEUE_NAME = "ros.wms.registered.queue"

async def call_ros_rest(order_id: str, destination: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.ROS_BASE_URL}/routes/assign",
            json={"order_id": order_id, "destination": destination},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


async def handle_message(message: aio_pika.IncomingMessage, exchange: aio_pika.Exchange):
    async with message.process():
        try:
            body = json.loads(message.body)
            order_id = body.get("order_id")
            destination = body.get("destination", "")
            logger.info(f"ROS Adapter: assigning route for order {order_id}")

            result = await call_ros_rest(order_id, destination)
            logger.info(f"ROS REST response: {result}")

            out_body = {
                "order_id": order_id,
                "route_id": result.get("route_id"),
                "driver_id": result.get("driver_id"),
                "estimated_delivery": result.get("estimated_delivery"),
            }
            out_msg = aio_pika.Message(
                body=json.dumps(out_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            )
            await exchange.publish(out_msg, routing_key="ros.route_assigned")
            logger.info(f"Published ros.route_assigned for order {order_id}")

        except Exception as e:
            logger.error(f"ROS Adapter error: {e}", exc_info=True)
            out_msg = aio_pika.Message(
                body=message.body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            )
            await exchange.publish(out_msg, routing_key="ros.driver_unavailable")
            logger.info(f"Published ros.driver_unavailable for order {order_id}")


async def main():
    await asyncio.sleep(10)
    logger.info("ROS Adapter connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    exchange = await channel.declare_exchange(
        settings.EXCHANGE_NAME,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )

    queue = await channel.declare_queue(QUEUE_NAME, durable=True)
    await queue.bind(exchange, routing_key="wms.registered")
    await queue.consume(lambda msg: handle_message(msg, exchange))

    logger.info(f"ROS Adapter listening on {QUEUE_NAME}")
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
