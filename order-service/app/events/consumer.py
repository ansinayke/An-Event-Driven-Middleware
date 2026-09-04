import json
import logging
import asyncio
import aio_pika
from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.models.order import Order, OrderStatus
from sqlalchemy import select

logger = logging.getLogger(__name__)

QUEUE_BINDINGS = {
    "order.service.cms.confirmed.queue": "cms.confirmed",
    "order.service.wms.registered.queue": "wms.registered",
    "order.service.ros.route_assigned.queue": "ros.route_assigned",
    "order.service.ros.driver_unavailable.queue": "ros.driver_unavailable",
}

STATUS_TRANSITIONS = {
    "cms.confirmed": OrderStatus.CMS_CONFIRMED,
    "wms.registered": OrderStatus.PACKAGE_REGISTERED,
    "ros.route_assigned": OrderStatus.ROUTE_ASSIGNED,
    "ros.driver_unavailable": OrderStatus.DRIVER_UNAVAILABLE,
}


async def handle_message(message: aio_pika.IncomingMessage, routing_key: str):
    async with message.process():
        try:
            body = json.loads(message.body)
            order_id = body.get("order_id")
            logger.info(f"Received event [{routing_key}] for order {order_id}")

            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Order).where(Order.id == order_id))
                order = result.scalar_one_or_none()
                if not order:
                    logger.warning(f"Order {order_id} not found")
                    return

                if routing_key == "cms.confirmed" and body.get("failed"):
                    order.status = OrderStatus.FAILED
                    order.failed_reason = "CMS rejected the order"
                    await db.commit()
                    logger.warning(f"Order {order_id} marked FAILED — CMS rejected")
                    from app.events.publisher import publish_event
                    await publish_event("order.compensate", {"order_id": order_id})
                    return

                new_status = STATUS_TRANSITIONS.get(routing_key)
                if new_status:
                    order.status = new_status
                    if new_status == OrderStatus.ROUTE_ASSIGNED:
                        order.driver_id = body.get("driver_id")
                    await db.commit()
                    logger.info(f"Order {order_id} status updated to {new_status} with driver_id {order.driver_id}")

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)


async def start_consumer():
    await asyncio.sleep(5)  
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
        logger.info(f"Consuming queue: {queue_name} bound to {routing_key}")

    logger.info("Order service consumer started.")
    await asyncio.Future() 
