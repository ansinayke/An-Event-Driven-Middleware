import asyncio
import json
import logging
import aio_pika
import httpx
import xml.etree.ElementTree as ET
from app.core.config import settings
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

QUEUE_NAME = "cms.order.created.queue"


CMS_SOAP_URL = getattr(settings, "CMS_SOAP_URL", "http://cms-mock:8020/soap/order")

async def call_cms_soap(order_id: str) -> dict:
    """Real HTTP SOAP integration."""
    soap_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cms="http://swifttrack.com/cms">
   <soapenv:Header/>
   <soapenv:Body>
      <cms:ProcessOrder>
         <cms:OrderId>{order_id}</cms:OrderId>
      </cms:ProcessOrder>
   </soapenv:Body>
</soapenv:Envelope>"""

    headers = {'Content-Type': 'text/xml; charset=utf-8'}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(CMS_SOAP_URL, content=soap_request, headers=headers, timeout=10.0)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            success = "true"
            reason = ""
            for elem in root.iter():
                if 'Success' in elem.tag:
                    success = elem.text.lower() if elem.text else "false"
                if 'Reason' in elem.tag:
                    reason = elem.text or ""
                    
            if success == "true":
                logger.info(f"SOAP call SUCCESS for order {order_id}")
                return {"success": True}
            else:
                logger.warning(f"SOAP call FAILED for order {order_id}: {reason}")
                return {"success": False, "reason": reason}
    except Exception as e:
        logger.error(f"SOAP call ERROR for order {order_id}: {e}")
        return {"success": False, "reason": "Network error reaching CMS"}


async def handle_message(message: aio_pika.IncomingMessage, exchange: aio_pika.Exchange):
    async with message.process():
        try:
            body = json.loads(message.body)
            order_id = body.get("order_id")
            logger.info(f"CMS Adapter received order.created for order {order_id}")

            result = await call_cms_soap(order_id)

            event_body = {
                "order_id": order_id,
                "failed": not result["success"],
            }
            if not result["success"]:
                event_body["reason"] = result.get("reason")

            out_msg = aio_pika.Message(
                body=json.dumps(event_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            )
            await exchange.publish(out_msg, routing_key="cms.confirmed")
            logger.info(f"Published cms.confirmed for order {order_id} | failed={event_body['failed']}")

        except Exception as e:
            logger.error(f"CMS Adapter error: {e}", exc_info=True)


async def main():
    await asyncio.sleep(8)  
    logger.info("CMS Adapter connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    exchange = await channel.declare_exchange(
        settings.EXCHANGE_NAME,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )

    queue = await channel.declare_queue(QUEUE_NAME, durable=True)
    await queue.bind(exchange, routing_key="order.created")
    await queue.consume(lambda msg: handle_message(msg, exchange))

    logger.info(f"CMS Adapter listening on {QUEUE_NAME}")
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
