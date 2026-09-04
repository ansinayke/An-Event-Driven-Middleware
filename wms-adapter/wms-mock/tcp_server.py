"""
Mock TCP server simulating the Warehouse Management System.
Listens on port 9000. Accepts JSON messages, returns JSON responses.
"""
import asyncio
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("wms-tcp-server")

HOST = "0.0.0.0"
PORT = 9000


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    logger.info(f"WMS TCP connection from {addr}")
    try:
        data = await reader.read(4096)
        message = json.loads(data.decode())
        order_id = message.get("order_id", "unknown")
        action = message.get("action", "register")

        if action == "register":
            logger.info(f"WMS registered package for order {order_id}")
            response = {"success": True, "order_id": order_id, "warehouse_ref": f"WH-{order_id[:8]}"}
        elif action == "compensate":
            logger.info(f"WMS rolling back registration for order {order_id}")
            response = {"success": True, "order_id": order_id, "action": "rolled_back"}
        else:
            response = {"success": False, "error": "Unknown action"}

        writer.write(json.dumps(response).encode())
        await writer.drain()
    except Exception as e:
        logger.error(f"WMS TCP error: {e}", exc_info=True)
    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    logger.info(f"WMS Mock TCP Server listening on {HOST}:{PORT}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
