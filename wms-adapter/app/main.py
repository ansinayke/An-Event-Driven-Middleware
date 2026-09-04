import asyncio
import json
import logging
import aio_pika
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ORDER_CREATED_QUEUE = "wms.order.created.queue"
COMPENSATE_QUEUE = "wms.order.compensate.queue"


async def call_wms_tcp(payload: dict) -> dict:
    """Open a TCP connection to the mock WMS server and send a JSON message."""
    reader, writer = await asyncio.open_connection(settings.WMS_TCP_HOST, settings.WMS_TCP_PORT)
    writer.write(json.dumps(payload).encode())
    await writer.drain()
    data = await reader.read(4096)
    writer.close()
    await writer.wait_closed()
    return json.loads(data.decode())


async def handle_order_created(message: aio_pika.IncomingMessage, exchange: aio_pika.Exchange):
    async with message.process():
        try:
            body = json.loads(message.body)
            order_id = body.get("order_id")
            logger.info(f"WMS Adapter: registering package for order {order_id}")

            response = await call_wms_tcp({"action": "register", "order_id": order_id})
            logger.info(f"WMS TCP response: {response}")

            out_body = {"order_id": order_id, "warehouse_ref": response.get("warehouse_ref")}
            out_msg = aio_pika.Message(
                body=json.dumps(out_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            )
            await exchange.publish(out_msg, routing_key="wms.registered")
            logger.info(f"Published wms.registered for order {order_id}")

        except Exception as e:
            logger.error(f"WMS Adapter error (order.created): {e}", exc_info=True)


async def handle_compensate(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            body = json.loads(message.body)
            order_id = body.get("order_id")
            logger.info(f"WMS Adapter: compensation request for order {order_id}")

            response = await call_wms_tcp({"action": "compensate", "order_id": order_id})
            logger.info(f"WMS compensation result: {response}")

        except Exception as e:
            logger.error(f"WMS Adapter error (order.compensate): {e}", exc_info=True)


async def main():
    await asyncio.sleep(10)
    logger.info("WMS Adapter connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    exchange = await channel.declare_exchange(
        settings.EXCHANGE_NAME,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )

    queue_created = await channel.declare_queue(ORDER_CREATED_QUEUE, durable=True)
    await queue_created.bind(exchange, routing_key="order.created")
    await queue_created.consume(lambda msg: handle_order_created(msg, exchange))

    queue_compensate = await channel.declare_queue(COMPENSATE_QUEUE, durable=True)
    await queue_compensate.bind(exchange, routing_key="order.compensate")
    await queue_compensate.consume(handle_compensate)

    logger.info("WMS Adapter listening for order.created and order.compensate")
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
